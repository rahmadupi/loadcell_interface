# Requires: pip install pyserial
import json
import subprocess
import serial.tools.list_ports

def _query_win_serial_ports():
    # run PowerShell to get Win32_SerialPort objects as JSON
    cmd = [
        "powershell", "-NoProfile", "-Command",
        "Get-CimInstance Win32_SerialPort | "
        "Select-Object DeviceID,Caption,PNPDeviceID | ConvertTo-Json -Compress"
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not proc.stdout.strip():
        return []
    data = json.loads(proc.stdout)
    # Normalize to list
    return data if isinstance(data, list) else [data]

def list_ports_with_friendly_names():
    ports = list(serial.tools.list_ports.comports())
    win_info = _query_win_serial_ports()
    # build map DeviceID -> Caption
    caption_by_device = {entry.get("DeviceID"): entry.get("Caption") for entry in win_info}
    results = []
    for p in ports:
        friendly = caption_by_device.get(p.device) or p.description or p.product or "<unknown>"
        results.append((p.device, friendly, p.hwid))
    return results

if __name__ == "__main__":
    for dev, name, hwid in list_ports_with_friendly_names():
        print(f"{dev} -> {name} [{hwid}]")