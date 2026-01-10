# import sys, os, time, random, json 
from pathlib import Path
from .loadcell import loadcell_controller
from .utility import interface, plotter
from .communication import serial_com

def main():
    serial= serial_com()
    loadcell = loadcell_controller(serial)
    plot = plotter(loadcell)
    # allow loadcell to publish readings to the plotter
    loadcell.plotter = plot
    interface_controller = interface(loadcell_controller=loadcell, plotter_controller=plot)
    loadcell.startup()
    interface_controller.run()

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"An error occurred: {e}")
        input("Press Enter to exit...")
        exit(1)