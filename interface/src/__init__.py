import subprocess

def get_version():
    """Get version from git tags"""
    try:
        # Run git describe --tags
        version = subprocess.check_output(
            ['git', 'describe', '--tags'],
            stderr=subprocess.DEVNULL,
            text=True
        ).strip()
        
        # Remove 'v' prefix if present
        if version.startswith('v'):
            version = version[1:]
        return version
    except:
        return "0.0.0-dev"  # Fallback if no git or tags

__version__ = get_version()
__license__ = "MIT"
__author__ = ""

# Expose main classes
from .main import main
from .communication import serial_com, COMMS_METHOD
from .loadcell import loadcell_controller, LOADCELL_MODE, LOADCELL_COMMAND
from .utility import interface, plotter, Color

__all__ = ['main', 'serial_com', 'COMMS_METHOD', 'loadcell_controller', 'LOADCELL_MODE', 'LOADCELL_COMMAND', 'interface', 'plotter',]