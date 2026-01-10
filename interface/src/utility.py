from enum import Enum, auto

from colorama import Fore, Back, Style
from . import __author__, __license__, __version__
from time import time,sleep
from .loadcell import LOADCELL_MODE
import threading
import colorama
import traceback
import os
import collections
import sys

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.animation as animation

try:
    import msvcrt
    _WINDOWS = True
except ImportError:
    import tty
    import termios
    import select
    _WINDOWS = False

colorama.init(autoreset=True)
class Color:
    RESET = Style.RESET_ALL

    # Foregrounds
    BLACK = Fore.BLACK
    RED = Fore.RED
    GREEN = Fore.GREEN
    YELLOW = Fore.YELLOW
    BLUE = Fore.BLUE
    MAGENTA = Fore.MAGENTA
    CYAN = Fore.CYAN
    WHITE = Fore.WHITE
    GRAY = Fore.LIGHTBLACK_EX

    # Bright variants
    BRIGHT_BLACK = Style.BRIGHT + Fore.BLACK
    BRIGHT_RED = Style.BRIGHT + Fore.RED
    BRIGHT_GREEN = Style.BRIGHT + Fore.GREEN
    BRIGHT_YELLOW = Style.BRIGHT + Fore.YELLOW
    BRIGHT_BLUE = Style.BRIGHT + Fore.BLUE
    BRIGHT_MAGENTA = Style.BRIGHT + Fore.MAGENTA
    BRIGHT_CYAN = Style.BRIGHT + Fore.CYAN
    BRIGHT_WHITE = Style.BRIGHT + Fore.WHITE

    @staticmethod
    def wrap(text: str, fore: str = None, back: str = None, bright: bool = False) -> str:
        parts = []
        if bright and fore:
            parts.append(Style.BRIGHT)
        if fore:
            parts.append(fore)
        if back:
            parts.append(back)
        parts.append(str(text))
        parts.append(Style.RESET_ALL)
        return "".join(parts)

    # convenience printers
    @staticmethod
    def info(text: str):
        print(Color.wrap(text, fore=Fore.CYAN))

    @staticmethod
    def success(text: str):
        print(Color.wrap(text, fore=Fore.GREEN,bright=True))

    @staticmethod
    def warn(text: str):
        print(Color.wrap(text, fore=Fore.YELLOW))

    @staticmethod
    def error(text: str):
        print(Color.wrap(text, fore=Fore.RED, bright=True))
        
    @staticmethod
    def gray(text: str):
        print(Color.wrap(text, fore=Color.GRAY))
        
    @staticmethod
    def chosen(text: str):
        print(Color.wrap(text, fore=Fore.WHITE, bright=True))
        
class Keyboard(Enum):
    ENTER = auto()
    ARROW_UP = auto()
    ARROW_DOWN = auto()
    ARROW_LEFT = auto()
    ARROW_RIGHT = auto()
    
class Keyboard(Enum):
    ENTER = auto()
    ARROW_UP = auto()
    ARROW_DOWN = auto()
    ARROW_LEFT = auto()
    ARROW_RIGHT = auto()
    ESCAPE = auto()
    
class keyboard:
    @staticmethod
    def read_key(timeout=None):
        if _WINDOWS:
            start = time() if timeout is not None else None
            while True:
                if msvcrt.kbhit():
                    ch = msvcrt.getwch()
                    if ch in ('\r', '\n'):
                        return Keyboard.ENTER
                    if ch == '\x1b':  # ESC key
                        return Keyboard.ESCAPE
                    if ch in ('\x00', '\xe0'):
                        code = msvcrt.getwch()
                        return {
                            'H': Keyboard.ARROW_UP,
                            'P': Keyboard.ARROW_DOWN,
                            'K': Keyboard.ARROW_LEFT,
                            'M': Keyboard.ARROW_RIGHT
                        }.get(code, ch)
                    return ch
                if timeout is not None and (time() - start) >= timeout:
                    return None
                sleep(0.01)
        else:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                if timeout is not None:
                    rlist, _, _ = select.select([sys.stdin], [], [], timeout)
                    if not rlist:
                        return None
                ch = sys.stdin.read(1)
                if not ch:
                    return None
                if ch == '\x1b':  # escape sequence
                    # peek for arrow keys or standalone ESC
                    rlist, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if rlist:
                        seq = sys.stdin.read(2)
                        if seq == '[A':
                            return Keyboard.ARROW_UP
                        if seq == '[B':
                            return Keyboard.ARROW_DOWN
                        if seq == '[C':
                            return Keyboard.ARROW_RIGHT
                        if seq == '[D':
                            return Keyboard.ARROW_LEFT
                        return 'OTHER'
                    else:
                        return Keyboard.ESCAPE
                if ch in ('\r', '\n'):
                    return Keyboard.ENTER
                return ch
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
    
class interface:
    def __init__(self, loadcell_controller=None, plotter_controller=None):
        self.loadcell = loadcell_controller
        self.plotter = plotter_controller
        
        self.option=0
        self.options={
            "MODE":["SET MODE"],
            "TARE":["SET TARE"],
            "CALIBRATE":["CALIBRATE"],
            "SCALE":["SET SCALE"],
            "GRAPH":["OPEN GRAPH", "CLOSE GRAPH"],
            "SET_PIN":["SET PIN"],
            "CONNECTION":["CLOSE CONNECTION","OPEN CONNECTION"],
        }
        
        self.graph_open=None
        self.intentional_disconnect=False
        
    def info(self):
        print(f"{' Loadcell Interface ':=^30}")
        Color.info(f"Version: {__version__}")
        Color.info(f"Author: {__author__}")
        # print(f"License: {__license__}")
        # print(f"{'':=^30}")
        
    def device_info(self):
        print(f"{' Device Information ':=^30}")
        loadcell_info=self.loadcell.info() if self.loadcell is not None else {}
        for k,v in loadcell_info.items():
            Color.info(f"{k}: {v}")
        print(f"{'':=^30}\n")
        current_reading=self.loadcell.get_current_reading()
        weight=current_reading/1000 if current_reading and current_reading>1500 else current_reading
        force=((current_reading/1000)*9.81)
        print(f"[W]: {weight:0.3f} {"g" if current_reading and current_reading<=1500 else "kg"}")
        print(f"[F]: {force:0.3f} N")
        Color.warn(f"[!] Set loadcell to ACTIVE mode to enable reading\n") if loadcell_info.get("mode") != LOADCELL_MODE.ACTIVE.name else print()
        
    def clear_console(self, FULL=True, lines=6):
        if FULL:
            os.system('cls' if os.name == 'nt' else 'clear')
        else:
        #    print("\033[6A", end="") 
           for _ in range(lines):
                print("\033[2K", end="")
                print("\033[1A", end="") 
        
    def run(self):
        while(True):    
            if not self.loadcell.status() and not self.intentional_disconnect:
                Color.error("Loadcell not connected.")
                Color.info("Attempting to reconnect...")
                self.loadcell.reconnect()
            self.clear_console()
            self.info()
            self.device_info()
            
            for i,(k,v) in enumerate(self.options.items()):
                if i==self.option:
                    if k=="GRAPH":
                        print(Color.wrap("[>]", fore=Fore.BLUE, bright=True) + Color.wrap(f" {v[1 if self.graph_open else 0]}", fore=Fore.WHITE, bright=True))
                    elif k=="CONNECTION":
                        print(Color.wrap("[>]", fore=Fore.BLUE, bright=True) + Color.wrap(f" {v[1 if not self.loadcell.status() else 0]}", fore=Fore.WHITE, bright=True))
                    else:
                        print(Color.wrap("[>]", fore=Fore.BLUE, bright=True) + Color.wrap(f" {v[0]}", fore=Fore.WHITE, bright=True))
                else:
                    if k=="GRAPH":
                        Color.gray(f"[ ] {v[1 if self.graph_open else 0]}")
                    elif k=="CONNECTION":
                        Color.gray(f"[ ] {v[1 if not self.loadcell.status() else 0]}")
                    else:
                        Color.gray(f"[ ] {v[0]}")
            try:
                opt_list=list(self.options.keys())
                selected_key=opt_list[self.option]
                keyboard_input=keyboard.read_key()
                if keyboard_input==Keyboard.ARROW_UP:
                    self.option-=1
                    if self.option<0:
                        self.option=len(self.options)-1
                elif keyboard_input==Keyboard.ARROW_DOWN:
                    self.option+=1
                    if self.option>=len(self.options):
                        self.option=0
                elif keyboard_input==Keyboard.ENTER:
                    if selected_key==opt_list[0]:  # MODE
                        self.set_mode()
                    elif selected_key==opt_list[1]:  # SET_TARE
                        self.set_tare()
                    elif selected_key==opt_list[2]:  # CALIBRATE
                        self.calibrate()
                    elif selected_key==opt_list[3]:  # SCALE
                        self.set_scale()
                    elif selected_key==opt_list[4]:  # GRAPH
                        self.toggle_graph()
                    elif selected_key==opt_list[5]:  # SET_PIN
                        self.set_pin()
                    elif selected_key==opt_list[6]:  # CONNECTION
                        self.open_close_connection()
            except Exception as e:
                print(e)
  
    def set_tare(self):
        input("Press Enter to set tare...")
        if (not self.loadcell.set_tare()):
            Color.error("[-] Failed to set tare.")
        else:
            Color.success("[+] Tare set successfully.")
        input("Press Enter to continue...")
            
    def set_mode(self):
        self.clear_console(False)
        try:
            available_modes=self.loadcell.available_mode()
            available_modes.pop(available_modes.index(self.loadcell.current_mode())) if self.loadcell.current_mode() in available_modes else None
            option=0
            
            Color.info("[X] Setting Mode")
            Color.info("Select Loadcell Mode:")
            while True:
                for i,mode in enumerate(available_modes):
                    if i==option:
                        print(Color.wrap("[>]", fore=Fore.BLUE, bright=True) + Color.wrap(f" {mode}", fore=Fore.WHITE, bright=True))
                    else:
                        Color.gray(f"[ ] {mode}")
                keyboard_input=keyboard.read_key()
                if keyboard_input==Keyboard.ARROW_UP:
                    option-=1
                    if option<0:
                        option=len(available_modes)-1
                elif keyboard_input==Keyboard.ARROW_DOWN:
                    option+=1
                    if option>=len(available_modes):
                        option=0
                elif keyboard_input==Keyboard.ENTER:
                    selected_mode=available_modes[option]
                    interval=None
                    print(f"Selected Mode: {selected_mode}")
                    if selected_mode is LOADCELL_MODE.RUN.name or selected_mode is LOADCELL_MODE.ACTIVE.name:
                        interval = input("Enter reading interval in hz\n> ")
                    if not self.loadcell.set_mode(LOADCELL_MODE[selected_mode], interval):
                        Color.error("[-] Failed to set mode.")
                    else:
                        Color.success(f"[+] Mode set to {selected_mode}.")
                    input("Press Enter to continue...")
                    return None
                elif keyboard_input==Keyboard.ESCAPE:
                    return None
                self.clear_console(False, lines=len(available_modes))
        except Exception as e:
            Color.error(f"[-] Failed to set mode: {e}")
            traceback.print_exc()
            input("Press Enter to continue...")
    
    def calibrate(self):
        try:
            self.clear_console(False)
            Color.info("[X] Calibration")
            
            step_list=[
                "Remove all weight from the loadcell",
                "Tareing and Zeroing scale",
                "Place the known weight on the loadcell",
                "Reading value from loadcell and calculating calibration factor",
            ]
            
            step=0
            for step in range(4):
                for enum, i in enumerate(step_list):
                    if enum==step:
                        print(Color.wrap(f"[{enum+1}]", fore=Fore.WHITE, bright=True) + Color.wrap(f" {i}", fore=Fore.WHITE, bright=True))
                    else:
                        Color.gray(f"[{enum+1}] {i}")
                
                if step==0:
                    while True:
                        try:
                            weight=float(input("Enter known weight in grams:\n> "))
                            if weight<=0:
                                Color.warn("[-] Weight must be positive.")
                            else:
                                break
                        except Exception as e:
                            Color.warn(f"Invalid weight: {e}")
                            input("Press Enter to retry...")
                            self.clear_console(False, lines=4)
                            continue
                    print(f"Known weight entered: {weight} g")
                    Color.warn("[!] Remove any weight from the loadcell")
                    sleep(0.5)
                    self.loadcell.calibrate(step, weight=weight)
                    input("Press Enter to continue...")
                    self.clear_console(False, lines=9)
                elif step==1:
                    print("Tareing and Zeroing scale...")
                    sleep(1)
                    self.loadcell.calibrate(step)
                    input("Press Enter to continue...")
                    self.clear_console(False, lines=6)
                elif step==2:
                    Color.warn(f"[!] Place the known weight of {weight} g on the loadcell")
                    sleep(1)
                    self.loadcell.calibrate(step)
                    input("Press Enter to continue...")
                    self.clear_console(False, lines=6)
                elif step==3:
                    print("Reading value from loadcell and calculating calibration factor...")
                    sleep(1)
                    self.loadcell.calibrate(step)
                    Color.success("[+] Calibration completed successfully.")
                    input("Press Enter to Complete...")
        except KeyboardInterrupt:
            Color.error("[-] Calibration cancelled by user.")
            input("Press Enter to continue...")
            return None
        except Exception as e:
            Color.error(f"[-] Calibration failed: {e}")
            traceback.print_exc()
            input("Press Enter to continue...")
            
    def set_scale(self):
        self.clear_console(False, lines=6)
        Color.info("[X] Set Scale Factor")
        try:
            scale_factor=None
            while True:
                try:
                    scale_factor=float(input("Enter new scale factor (e.g., 400.0):\n> "))
                    if scale_factor<=0:
                        Color.error("[-] Scale factor must be positive.")
                        input("Press Enter to continue...")
                        continue
                    else:
                        break
                except Exception as e:
                    Color.error(f"[-] Invalid scale factor: {e}")
                    input("Press Enter to retry...")
                    self.clear_console(False, lines=4)
                    continue
        except KeyboardInterrupt:
            Color.error("[-] Set scale factor cancelled by user.")
            input("Press Enter to continue...")
            return None
        except Exception as e:
            Color.error(f"[-] Failed to set scale factor: {e}")
            traceback.print_exc()
            input("Press Enter to continue...")
        
        print(f"Setting scale factor to: {scale_factor}")
        self.loadcell.set_scale(scale_factor)
        Color.success("[+] Scale factor set successfully.")
        input("Press Enter to continue...")
    
    def toggle_graph(self):
        if self.graph_open:
            # Close graph
            self.graph_open = False
            if self.plotter and self.plotter.is_active():
                self.plotter.stop()
            Color.info("[X] Graph closed.")
        else:
            # Open graph
            self.clear_console(False, lines=6)
            Color.info("[X] Opening graph")
            loadcell_status = self.loadcell.info()
            try:
                if loadcell_status['mode'] != LOADCELL_MODE.ACTIVE.name or not loadcell_status['connected']:
                    Color.warn("[-] Please set loadcell to ACTIVE mode and ensure it is connected to open the graph.")
                    self.graph_open = False
                    input("Press Enter to continue...")
                    return None
                hertz, time_scale = 0,0
                while True:
                    try:
                        if not hertz:
                            hertz=int(input("Enter refresh rate in Hz (e.g., 20):\n> "))
                            if hertz<=0:
                                raise ValueError("Refresh rate must be positive.")
                    except Exception as e:
                        print(f"Invalid refresh rate: {e}")
                        input("Press Enter to retry...")
                        continue
                    
                    try:
                        time_scale=float(input("Enter time scale (seconds displayed on x-axis, e.g., 3.0):\n> "))
                        if time_scale<=0:
                            raise ValueError("Time scale must be positive.")
                        else:
                            break
                    except Exception as e:
                        print(f"Invalid time scale: {e}")
                        input("Press Enter to retry...")
                        continue
                interval=int(1000/hertz) if hertz>0 else 50
                success = self.plotter.start(interval_ms=interval, time_scale=time_scale)
                self.graph_open = True
                if success:
                    self.graph_open = False
                    Color.success("[+] Graph opened in separate window.")
                    
                else:
                    Color.error("[-] Failed to start plotter")
                    
            except Exception as e:
                Color.error(f"[-] Failed to open graph: {e}")
                tb = traceback.format_exc()
                Color.gray(tb)
                self.graph_open = False
        
        input("Press Enter to continue...")
            
    
    def open_close_connection(self):
        if self.loadcell.status():
            self.intentional_disconnect=True
            self.loadcell.close()
            Color.warn("[+] Connection closed.")
        else:
            self.intentional_disconnect=False
            self.loadcell.reconnect()
            self.loadcell.startup()
            Color.success("[+] Connection opened.")
        input("Press Enter to close connection...")
    
    def set_pin(self):
        self.clear_console(False)
        Color.info("[X] Set PIN")
        pin = input("Enter new PIN (4Digit Number)\n> ")
        if not pin.isdigit() or len(pin)!=4:
            Color.error("[-] Invalid PIN format. PIN must be a 4-digit number.")
            input("Press Enter to continue...")
            return None
        else:
            if not self.loadcell.set_pin(pin):
                Color.error("[-] Failed to set PIN.")
            else:
                Color.success("[+] PIN set successfully.")
            input("Press Enter to continue...")

class plotter:
    def __init__(self, loadcell_controller=None):
        self.loadcell = loadcell_controller
        self.weight_g=0.0
        self.force_n=0.0
        
        # Graph state
        self.is_running = False
        self.plot_thread = None
        self.stop_plot = threading.Event()
        
        # Data storage (thread-safe)
        self.data_lock = threading.Lock()
        self.max_points = 100  # sliding window size
        self.data = None
        self.times = None
        
        # Matplotlib objects
        self.fig = None
        self.ax = None
        self.line = None
        self.animation = None
        
        # Configuration
        self.interval_ms = 200  # update interval
        self.time_scale = 1.0   # time axis scaling
        self.window_seconds = 0
        self.start_time = None
    
    # ===== PUBLIC API =====
    
    def start(self, interval_ms=200, time_scale=3.0):
        
        if self.is_running:
            Color.warn("[!] Plotter is already running")
            return False
        
        # Update configuration
        self.max_points = 100
        self.interval_ms = interval_ms
        self.time_scale = time_scale
        dt = (interval_ms / 1000.0)
        dt_scaled = dt * float(time_scale)
        self.window_seconds = self.max_points * dt_scaled
        
        self.weight_data = collections.deque(maxlen=self.max_points)
        self.force_data = collections.deque(maxlen=self.max_points)
        self.times = collections.deque(maxlen=self.max_points)
        
        # Start plot in the main thread (required by GUI backends)
        self.stop_plot.clear()
        self.is_running = True
        self.plot_thread = None

        try:
            # Run the plot worker directly on the calling (main) thread.
            # This will block until the plot window is closed.
            self._plot_worker()
        finally:
            # Ensure state is cleaned up when the plot finishes
            self.is_running = False

        Color.success("[+] Plotter finished")
        return True
    
    def stop(self):
        """Stop the live plot and close the window gracefully."""
        if not self.is_running:
            return
            
        self.stop_plot.set()
        self.is_running = False
        
        # Close matplotlib window if open
        try:
            import matplotlib.pyplot as plt
            if self.fig is not None:
                plt.close(self.fig)
        except Exception:
            pass
        
        # Wait for thread to finish (don't join current thread)
        try:
            if self.plot_thread and self.plot_thread.is_alive() and threading.current_thread() is not self.plot_thread:
                self.plot_thread.join(timeout=2.0)
        except RuntimeError:
            # In case current thread cannot join itself, just skip
            pass
        
        Color.info("[X] Plotter stopped")
        self.graph_open = False
    
    def is_active(self):
        """Check if plotter is currently running."""
        return self.is_running
    
    # ===== INTERNAL METHODS =====
    def _initialize_plot(self):
        """Create matplotlib figure with dual y-axes for weight and force."""
        try:
            import matplotlib.pyplot as plt
            
            self.fig, self.ax1 = plt.subplots(figsize=(12, 6))
            
            # Set window title and hide toolbar
            try:
                self.fig.canvas.manager.set_window_title("Load Cell Live - Weight & Force")
                mgr = plt.get_current_fig_manager()
                mgr.toolbar_visible = False
            except Exception:
                pass
            
            # Left y-axis: Weight (blue)
            self.line_weight, = self.ax1.plot([], [], marker='.', markersize=2, 
                                              linestyle='-', color='blue', label='Weight (kg)', linewidth=1.5)
            self.ax1.set_xlabel('Time (s)')
            self.ax1.set_ylabel('Weight (kg)', color='blue')
            self.ax1.tick_params(axis='y', labelcolor='blue')
            self.ax1.set_xlim(0, self.window_seconds)
            self.ax1.set_ylim(-0.1, 0.1)
            self.ax1.grid(True, alpha=0.3)
            
            # Right y-axis: Force (orange)
            self.ax2 = self.ax1.twinx()
            self.line_force, = self.ax2.plot([], [], marker='.', markersize=2,
                                             linestyle='-', color='orange', label='Force (N)', linewidth=1.5)
            self.ax2.set_ylabel('Force (N)', color='orange')
            self.ax2.tick_params(axis='y', labelcolor='orange')
            self.ax2.set_ylim(-1, 1)
            
            # Add legend
            lines = [self.line_weight, self.line_force]
            labels = [l.get_label() for l in lines]
            self.ax1.legend(lines, labels, loc='upper left')
            
            # Title
            self.ax1.set_title('Live Load Cell Data - Weight & Force')
            
            # Connect close event
            self.fig.canvas.mpl_connect('close_event', self._on_close)
            
            plt.tight_layout()
            
        except Exception as e:
            Color.error(f"[-] Failed to initialize plot: {e}")
            self.is_running = False
            raise
    
    def _prefill_data(self):
        """Prefill times and data deques with zeros for smooth initial rendering."""
        dt = (self.interval_ms / 1000.0)
        dt_scaled = dt * float(self.time_scale)
        
        with self.data_lock:
            self.times.extend([i * dt_scaled - self.window_seconds for i in range(self.max_points)])
            self.weight_data.extend([0.0] * self.max_points)
            self.force_data.extend([0.0] * self.max_points)
    
    def _plot_worker(self):
        """Background thread worker that runs the matplotlib event loop."""
        try:
            # matplotlib and pyplot already imported at module level
            # Try different backends until we find one that works
            backends_to_try = ['WXAgg', 'TkAgg'] #Qt5Agg
            
            for backend_name in backends_to_try:
                try:
                    matplotlib.use(backend_name, force=True)
                    Color.info(f"[O] Using matplotlib backend: {backend_name}")
                    break
                except (ImportError, ModuleNotFoundError):
                    continue
            else:
                # No interactive backend available
                Color.error("[-] No interactive matplotlib backend available!")
                Color.warn("[!] Install PyQt5 for interactive plotting: pip install PyQt5")
                return
            
            # Initialize plot
            self._initialize_plot()
            self._prefill_data()
            
            # Record start time
            self.start_time = time()
            
            # Create animation (keep reference to prevent garbage collection)
            anim = animation.FuncAnimation(
                self.fig,
                self._update_frame,
                interval=self.interval_ms,
                blit=False,
                cache_frame_data=False
            )
            self.animation = anim  # Store reference
            
            # Show plot (blocks until window closes)
            plt.show(block=True)
            
        except Exception as e:
            Color.error(f"[-] Plot worker error: {e}")
            tb = traceback.format_exc()
            Color.gray(tb)
        finally:
            self.is_running = False
            self.stop_plot.set()
    
    def _update_frame(self, frame):
        """
        Animation callback function called every interval_ms.
        
        Args:
            frame: Frame number from FuncAnimation (unused)
            
        Returns:
            tuple: (line_weight, line_force) for matplotlib animation
        """
        
        if self.stop_plot.is_set():
            return (self.line_weight, self.line_force)
        
        try:
            self._get_current_value()
            # Get current timestamp
            now = time() - self.start_time
            
            # Get weight and calculate force
            weight_kg = self.weight_g / 1000
            force_n = (weight_kg) * 9.81  # Convert g to kg, then to Newtons
            
            # Append to data (thread-safe)
            with self.data_lock:
                self.times.append(now)
                self.weight_data.append(weight_kg)
                self.force_data.append(force_n)
            
            # Update line data
            if len(self.times) > 0:
                with self.data_lock:
                    times_list = list(self.times)
                    weight_list = list(self.weight_data)
                    force_list = list(self.force_data)
                
                self.line_weight.set_data(times_list, weight_list)
                self.line_force.set_data(times_list, force_list)
                
                # Scroll x-axis
                tmax = times_list[-1]
                tmin = max(0.0, tmax - self.window_seconds)
                self.ax1.set_xlim(tmin, tmax)
                
                # Auto-adjust y-axes if needed
                self._adjust_y_limits(weight_list, force_list)
            else:
                self.line_weight.set_data([], [])
                self.line_force.set_data([], [])
                self.ax1.set_xlim(0, self.window_seconds)
            
        except Exception as e:
            Color.error(f"[-] Update frame error: {e}")
        
        return (self.line_weight, self.line_force)
    
    def _get_current_value(self):
        """
        Thread-safe getter for current loadcell reading.
        Converts grams to Newtons (F = m * g).
        
        Returns:
            float: Current force value in Newtons or 0.0 if unavailable
        """
        try:
            reading = self.loadcell.get_current_reading()
            if reading is not None:
                self.weight_g = reading
                self.force_n = (self.weight_g * 9.81)/1000  # Convert g to kg, then to Newtons
            return 0.0
        except Exception:
            return 0.0
    
    def _adjust_y_limits(self, weight_list, force_list):
        """
        Auto-scale both y-axes based on current data ranges.
        Adds 10% padding for visual clarity.
        
        Args:
            weight_list: List of current weight values (grams)
            force_list: List of current force values (Newtons)
        """
        if len(weight_list) == 0 or len(force_list) == 0:
            return
        
        try:
            # Adjust weight axis (ax1)
            ymin1, ymax1 = self.ax1.get_ylim()
            wmin = min(weight_list)
            wmax = max(weight_list)
            
            if wmin < ymin1 or wmax > ymax1:
                padding = (wmax - wmin) * 0.1 if wmax != wmin else 1.0
                self.ax1.set_ylim(wmin - padding, wmax + padding)
            
            # Adjust force axis (ax2)
            ymin2, ymax2 = self.ax2.get_ylim()
            fmin = min(force_list)
            fmax = max(force_list)
            
            if fmin < ymin2 or fmax > ymax2:
                padding = (fmax - fmin) * 0.1 if fmax != fmin else 0.1
                self.ax2.set_ylim(fmin - padding, fmax + padding)
        except Exception:
            pass
    
    def _on_close(self, event):
        """Matplotlib window close event handler."""
        self.stop()
        
    