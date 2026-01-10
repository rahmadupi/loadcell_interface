from enum import Enum, auto
from threading import Lock, Thread, Event
from time import sleep
import os
import struct


class LOADCELL_MODE(Enum):
    SETUP = 0
    RUN = auto()
    ACTIVE = auto()
    STOP = auto()
    CALIBRATE = auto()
    
class LOADCELL_COMMAND(Enum):
    PING = 0
    RESET_DEFAULT=auto()
    GET_MODE=auto()
    GET_READING=auto()
    SET_PIN=auto()
    SET_MODE=auto()
    SET_TARE=auto()
    SET_SCALE=auto()
    
class loadcell_controller:
    def __init__(self, comms_controller):
        self.comms = comms_controller
        self.reading=0.0
        self.mode=LOADCELL_MODE.RUN
        self.reading_thread = None
        self.stop_reading = Event()
        self.lock = Lock()
        
        # self.startup()
        
    def info(self):
        return {
            "mode": self.mode.name,
            "connected": self.comms.is_connected(),
            "comm_method": self.comms.device.name,
            "port": self.comms.ser.port if self.comms.ser else "None"
        }
        
    def get_current_reading(self):
        with self.lock:
            return self.reading if self.status() else 0.0
        
    def startup(self):
        if not self.comms.is_connected():
            self.comms.connect()
            
        self.get_mode() 
        self.start_reading_loop()

    def status(self):
        return self.comms.is_connected()
    
    def reconnect(self):
        if self.comms.is_connected():
            self.comms.close()
        while not self.comms.connect():
            os.system('cls' if os.name == 'nt' else 'clear')
        self.startup()
        
    def close(self):
        self.set_mode(LOADCELL_MODE.RUN)
        self.stop_reading_loop()
        self.comms.close()
    
    def current_mode(self):
        return self.mode.name   
    
    def available_mode(self):
        return [LOADCELL_MODE.RUN.name, LOADCELL_MODE.ACTIVE.name, LOADCELL_MODE.STOP.name]
    
    def start_reading_loop(self):
        """Start background thread for continuous reading."""
        if self.reading_thread is None or not self.reading_thread.is_alive():
            self.stop_reading.clear()
            self.reading_thread = Thread(target=self._reading_loop_worker, daemon=True, name="loadcellreadthread")
            self.reading_thread.start()
            # print("Loadcell reading loop started.")
            # input("Press Enter to continue...")
    
    def stop_reading_loop(self):
        """Stop the reading loop thread gracefully."""
        if self.reading_thread and self.reading_thread.is_alive():
            self.stop_reading.set()
            self.reading_thread.join(timeout=2.0)
            self.reading_thread = None
    
    def _reading_loop_worker(self):
        """Background worker that continuously reads data from device."""
        while not self.stop_reading.is_set():
            if self.comms.is_connected() and self.mode == LOADCELL_MODE.ACTIVE:
                self.reading_loop()
            else:
                sleep(0.5)
    
    def reading_loop(self):
        response=self.comms.read(timeout=500)
        if response:
            data=response[1][1:]
            if len(data)>=4:
                # with self.lock:
                self.reading = struct.unpack('<f', bytes(data[:4]))[0]
                # print(f"Loadcell Reading: {self.reading} g")
                # input("Press Enter to continueLaodcell...")
                # publish to plotter if available
                try:
                    if hasattr(self, 'plotter') and self.plotter is not None:
                        self.plotter.publish(self.reading)
                except Exception:
                    pass
            else:
                # with self.lock:
                self.reading = 0.0
        else:
            # with self.lock:
            self.reading = 0.0
        
    # Available commands
    def ping(self):
        data_sent=[LOADCELL_COMMAND.PING.value]
        self.comms.write(data_sent, header=True, convert_to_bytes=True) 
        response=self.comms.read(timeout=500)
        if response[0]=="response":
            res=response[1][0]
            return LOADCELL_COMMAND(res)==LOADCELL_COMMAND.PING
        return False
    
    def reset(self):
        data_sent=[LOADCELL_COMMAND.RESET_DEFAULT.value]
        self.comms.write(data_sent, header=True, convert_to_bytes=True)
        return True
    
    def get_mode(self):
        mode=None
        data_sent=[LOADCELL_COMMAND.GET_MODE.value]
        self.comms.write(data_sent, header=True, convert_to_bytes=True)
        response=self.comms.read(timeout=500, debug=True)
        if response and response[0]=="response":
            mode_value=response[1][0]
            mode=LOADCELL_MODE(mode_value).name
            self.mode=LOADCELL_MODE(mode_value)
        return mode
    
    def set_mode(self, mode: LOADCELL_MODE, interval=None):
        data_sent=[LOADCELL_COMMAND.SET_MODE.value,mode.value]
        if interval is not None:
            data_sent.append(int(interval))
        self.comms.write(data_sent, header=True, convert_to_bytes=True)
        self.mode=mode
        return True
    
    def set_tare(self):
        data_sent=[LOADCELL_COMMAND.SET_TARE.value]
        self.comms.write(data_sent, header=True, convert_to_bytes=True)
        return True
        
    # def get_scale(self):
    #     #TODO
    #     pass
    
    def set_pin(self, pin: str):
        data_sent=[LOADCELL_COMMAND.SET_PIN.value]
        data_sent.append(pin)
        self.comms.write(data_sent, header=True, convert_to_bytes=True)
        return True
    
    def calibrate(self, step=0, weight: float=0.0):
        data_sent=[LOADCELL_COMMAND.SET_MODE.value, LOADCELL_MODE.CALIBRATE.value, step]
        if weight>0.0:
            data_sent.append(weight)
            print(f"Calibrating with weight: {weight} g")
        self.comms.write(data_sent, header=True, convert_to_bytes=True)
        return True
    
    def set_scale(self, scale: float):
        data_sent=[LOADCELL_COMMAND.SET_SCALE.value]
        data_sent.append(scale)
        self.comms.write(data_sent, header=True, convert_to_bytes=True)
        return True
    