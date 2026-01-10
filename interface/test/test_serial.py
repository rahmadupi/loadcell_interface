from serial import Serial, SerialException
from threading import Lock
import time

_lock = Lock()

def open_com(port="COM16", baud=115200, timeout=1):
    try:
        return Serial(port, baudrate=baud, timeout=timeout)
    except SerialException:
        # Windows alternate device path if needed
        return Serial(r"\\.\%s" % port, baudrate=baud, timeout=timeout)

def main():
    startup_time = time.time()
    sent_time = time.time()
    print(f"startup {startup_time}")
    data=[0xFD,0x00,0x01,0x00]
    try:
        with open_com("COM16", 115200, timeout=1) as s:
            # send a command / probe
            for i in range(3):
                print(f"--- Iteration {i+1} --- {time.time()} since startup {time.time() - startup_time:.2f}s")
                sent_time = time.time()
                with _lock:
                    bytes_data=bytes(data)
                    print("TX:", bytes_data)
                    s.write(bytes_data)
                    s.flush()

                # short pause, then read available lines until timeout
                with _lock:
                    while True:
                        if s.in_waiting:
                            line = s.readline()
                            print("RX:", line)
                            print(f"after {time.time() - sent_time:.2f}s since sent")
                            if not line:
                                continue
                            else:
                                break
    except SerialException as e:
        print("Serial error:", e)

if __name__ == "__main__":
    main()
    # data=[0x03,0x25]
    # bytes_data=bytes(data)
    # print(bytes_data)