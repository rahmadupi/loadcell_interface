# ...existing code...
import re
import json
import sys
import time
import subprocess
from serial import Serial, SerialException
import serial.tools.list_ports

def run_ps(cmd, timeout=3):
    try:
        proc = subprocess.run(["powershell", "-NoProfile", "-Command", cmd],
                              capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as e:
        return 1, "", str(e)

def print_header(title):
    print("\n" + "="*6 + " " + title + " " + "="*6)

def list_com_ports():
    print_header("serial.tools.list_ports")
    for p in serial.tools.list_ports.comports():
        print(f"PORT: {p.device} | desc: {p.description!r} | product: {p.product!r} | hwid: {p.hwid!r} | pid: {p.pid} | vid: {p.vid}")

def query_win32_serialport(timeout=3):
    """Return mapping DeviceID -> dict(PNPDeviceID, Caption) for Win32_SerialPort."""
    code = "Get-CimInstance Win32_SerialPort | Select-Object DeviceID,PNPDeviceID,Caption | ConvertTo-Json -Compress"
    rc, out, err = run_ps(code, timeout=timeout)
    if rc != 0 or not out:
        return {}
    try:
        data = json.loads(out)
    except Exception:
        return {}
    items = data if isinstance(data, list) else [data]
    mapping = {}
    for it in items:
        dev = it.get("DeviceID")
        if dev:
            mapping[dev] = it
    return mapping

def query_win32_pnp_entities(filter_like="ESP"):
    print_header(f"Win32_PnPEntity (Caption/Name) containing '{filter_like}'")
    # use filter to limit output for speed; remove Where-Object if you want full list
    code = (
        f"Get-CimInstance Win32_PnPEntity | "
        f"Where-Object {{ ($_.Caption -like '*{filter_like}*') -or ($_.Name -like '*{filter_like}*') }} | "
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
        return []
    items = j if isinstance(j, list) else [j]
    for it in items:
        print(f"PNPDeviceID: {it.get('PNPDeviceID')!r} | Caption: {it.get('Caption')!r} | Name: {it.get('Name')!r}")
    return items

if __name__ == "__main__":
    # list_com_ports()
    # serial_map = query_win32_serialport()
    pnp_items = query_win32_pnp_entities("ESP")
    key=pnp_items[0]['PNPDeviceID'].split("\\")[1].split("_")[1]
    
    ports = list(serial.tools.list_ports.comports())

    for port in ports:
        if key in port.hwid:
            print(f"Matched COM port: {port.device} for PNPDeviceID containing '{key}'")

    # try to map each found PnP entity to a COM port
    
# ...existing code...