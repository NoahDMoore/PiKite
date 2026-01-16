import platform
import subprocess

from utils.logger import get_logger

# Setup Logger
logger = get_logger(__name__)

# Shutdown/Reboot Methods

def shutdown():
    """Shut down the computer based on the OS."""
    os_name = platform.system()

    try:
        if os_name == "Linux" or os_name == "Darwin":  # Darwin is macOS
            subprocess.run(["sudo", "nohup", "shutdown", "-h", "now"], check=True)
        elif os_name == "Windows":
            subprocess.run(["shutdown", "/s", "/t", "0"], check=True)
        else:
            raise ValueError(f"Unsupported OS: {os_name}")
    except ValueError as e:
        logger.error(f"Value Error: {e}. Shutdown aborted.")
    except Exception as e:
        logger.error(f"Shutdown failed: {e}")

def reboot():
    """Reboot the computer based on the OS."""
    os_name = platform.system()

    try:
        if os_name == "Linux" or os_name == "Darwin":
            subprocess.run(["sudo", "reboot"], check=True)
        elif os_name == "Windows":
            subprocess.run(["shutdown", "/r", "/t", "0"], check=True)
        else:
            raise ValueError(f"Unsupported OS: {os_name}")
    except ValueError as e:
        logger.error(f"Value Error: {e}. Reboot aborted.")
    except Exception as e:
        logger.error(f"Reboot failed: {e}")