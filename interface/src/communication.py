from serial import Serial
from time import time,sleep
from enum import Enum, auto
from .utility import Color
import serial.tools.list_ports
import threading
import json
import subprocess
import os
import struct
import traceback

class COMMS_METHOD(Enum):
    SERIAL_COM = 0
    BLUETOOTH_COM = auto()
    NO_CONNECTION = auto()
 
class serial_com():
    def __init__(self):
        self.read_lock = threading.Lock()
        self.write_lock = threading.Lock()
        self.device = None
        self.connected = False
        self.ser = None 
        
        self.connect()
    
    def connect(self, baudrate=115200, timeout=100):
        # try:
        #     raise Exception  # Force going to except block
        # except Exception:
        #     #print stack
        #     traceback.print_stack()
        # Connect Bluetooth First
        def run_ps(cmd, timeout=3):
            try:
                proc = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                                    capture_output=True, text=True, timeout=timeout)
                return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
            except Exception as e:
                return 1, "", str(e)
        code = (
            f"Get-CimInstance Win32_PnPEntity | "
            f"Where-Object {{ ($_.Caption -like '*{"ESP"}*') -or ($_.Name -like '*{"ESP"}*') }} | "
            "Select-Object PNPDeviceID,Caption,Name | ConvertTo-Json -Compress"
        )
        rc, out, err = run_ps(code)
        if rc != 0 or not out:
            print("No matching Win32_PnPEntity (rc,err):", rc, err)
            return []
        try:
            j = json.loads(out)
        except Exception as e:
            print("JSON parse error:", e)
        device = j if isinstance(j, list) else [j]
        # for it in items:
        #     print(f"PNPDeviceID: {it.get('PNPDeviceID')!r} | Caption: {it.get('Caption')!r} | Name: {it.get('Name')!r}")
        bt_device_key=device[0]['PNPDeviceID'].split("\\")[1].split("_")[1]
        
        data_sent = [0x00]
        ports = list(serial.tools.list_ports.comports())
        for port in ports:
            # print(f"Checking: {port.device}")
            # print(port.description)
            try:
                if bt_device_key and bt_device_key in port.hwid:
                    print(f"Attempting Bluetooth connection on {port.device}...")
                    try:
                        self.ser = Serial(port.device, baudrate=baudrate, timeout=1)
                    except Exception as e:
                        print(f"Failed to open bluetooth port {port.device}: {e}")
                        continue
                    self.write(data_sent, header=True, convert_to_bytes=True, debug=False)
                    resp = self.read(timeout=timeout)
                    if resp[1][0]==0x00:
                        print(f"Connected to {port.device} at {baudrate} baud. Response: {resp}")
                        self.device = COMMS_METHOD.BLUETOOTH_COM
                        return self.is_connected()
                    else:
                        print("Bluetooth device not responding correctly.")
                    continue
                    
                if "USB" in port.description and port.vid in (0x10C4,0x6970,0x1A86,0x303A):
                    print(f"Attempting Serial connection on {port.device}...")
                    try:
                        self.ser = Serial(port.device, baudrate=baudrate, timeout=1)
                    except Exception as e:
                        print(f"Failed to open serial port {port.device}: {e}")
                        continue
                    self.write(data_sent, header=True, convert_to_bytes=True, debug=False)
                    resp = self.read(timeout=timeout)
                    if resp[1][0]==0x00:
                        print(f"Connected to {port.device} at {baudrate} baud. Response: {resp}")
                        self.device = COMMS_METHOD.SERIAL_COM
                        return self.is_connected()
                    else:
                        print("Serial device not responding correctly.")
                    continue
            except Exception as e:
                print(e)
                
        if self.ser is None or not self.ser.is_open:
            print("Failed to connect to any serial port.")
            self.connected = False
            
    def convert_to_bytes(self, data):
        """
        Convert a list of mixed data types to bytes.
        
        Args:
            data: List containing integers, strings, and/or floats
            
        Returns:
            bytes: Byte representation of the data
            
        Examples:
            [0, 1, 2] -> b'\x00\x01\x02'
            [0, "PIN"] -> b'\x00PIN'
            [0, 1, 100.5] -> b'\x00\x01' + struct.pack('<f', 100.5)
        """
        result = []
        for item in data:
            if isinstance(item, int):
                if 0 <= item < 100:
                    result.append(item)
                elif 100 <= item <= 65535:
                    result.extend(list(struct.pack('<I', item)))
                else:
                    raise ValueError(f"Integer {item} out of range (0-65535)")
            elif isinstance(item, str):
                # String: convert to UTF-8 bytes
                result.extend(list(item.encode('utf-8')))
            elif isinstance(item, float):
                # Float: pack as little-endian 4-byte float
                result.extend(list(struct.pack('<f', item)))
            else:
                raise TypeError(f"Unsupported data type: {type(item)}")
        
        return bytes(result)
    
    def write(self, data, header=True, convert_to_bytes=False, debug=False):
        try:
            if convert_to_bytes:
                byte_data = self.convert_to_bytes(data)
            else:
                byte_data = data
            # Ensure we operate on the byte representation for length/header
            if not isinstance(byte_data, (bytes, bytearray)):
                try:
                    byte_data = bytes(byte_data)
                except Exception:
                    pass

            payload = byte_data
            if header:
                payload = bytes([0xFD, 0x00, len(byte_data)]) + byte_data

            if debug:
                Color.error(f"Actual data: {data}")
                Color.error(f"Writing data: {payload}")
                input("Press Enter to Leave Write Debug ...")
            try:
                with self.write_lock:
                    if self.ser is not None and self.ser.is_open:
                        self.ser.write(payload)
                        return True
            except Exception as e:
                print(f"Write error: {e}")
                return False
        except Exception as e:
            print(f"Conversion error: {e}")
            traceback.print_exc()
            input("Press Enter to continue...")
            return False
    
    def read(self, timeout=100, debug=False): #ms
        if self.ser is not None and not self.ser.is_open:
            return
    
        end_timeout = time() + (timeout / 1000.0)
        while time() < end_timeout:
            # Only lock when checking/reading from serial port
            with self.read_lock:
                if self.ser.in_waiting > 0:
                    # print(self.ser.readline())
                    if self.ser.read(1) != b'\xFD':
                        continue
                    if self.ser.read(1) != b'\x00':
                        continue

                    data_len = self.ser.read(1)
                    data = self.ser.read(int.from_bytes(data_len, byteorder='little'))
                    if debug:
                        Color.error(f"Read data: {data}")
                        input("Press Enter to Leave Read Debug ...")

                    return ["response", list(data)]
            
            # Release lock between iterations - allow other threads to write
            sleep(0.001)  # Small delay to prevent busy-waiting
        
        return ["timeout", []]
    
    def is_connected(self):
        try:
            self.connected =self.ser and self.ser.is_open
        except Exception:
            self.connected = False  
        return self.connected
    
    def connection_method(self):
        return self.device.name if self.device else COMMS_METHOD.NO_CONNECTION.name
        
    def close(self):
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.device = COMMS_METHOD.NO_CONNECTION
            
    def info(self):
        return {
            "device": self.connection_method(),
            "connected": self.connected,
            "port": self.ser.port if self.ser else None,
            "baudrate": self.ser.baudrate if self.ser else None,
        }