# pikite/core/constants.py
from enum import Enum

# Constants for XML tags and menu actions
class XMLTAG(str, Enum):
    MENU = "menu"
    MENU_ITEM = "menu_item"
    OPTION_ITEM = "option_item"
    SETTING = "setting"

class XMLATTRIB(str, Enum):
    NAME = "name"
    MESSAGE = "message"
    ACTION = "action"
    SETTING = "setting"
    VALUE = "value"

class MENUACTION (str, Enum):
    """
    Menu actions supported by PiKite

    Actions:
        SUBMENU:
            Navigate to a submenu
        RETURN:
            Return to the previous menu / exit a submenu
        OPTIONS:
            Open the options menu for the current menu item
        SELECT_OPTION:
            Select an option from the options menu
        LOAD_DEFAULTS:
            Load the default settings from the default configuration file
        DISPLAY_SYSTEM_INFO:
            Display system information on the screen
        SHUTDOWN:
            Shutdown the Raspberry Pi safely
        REBOOT:
            Reboot the Raspberry Pi safely
    """
    SUBMENU = "submenu"
    RETURN = "return"
    OPTIONS = "options"
    SELECT_OPTION = "selectOption"
    LOAD_DEFAULTS = "load_defaults"
    DISPLAY_SYSTEM_INFO = "display_system_info"
    SHUTDOWN = "shutdown"
    REBOOT = "reboot"

# Constandts for Camera
class CAPTURE_MODES(str, Enum):
    """
    Camera capture modes supported by PiKite
    
    STILL:
        Capture high-resolution still images
    VIDEO:
        Record video at a lower resolution
    NONE:
        Preview mode, no capture
    """

    STILL = "pic"
    VIDEO = "vid"
    NONE = "none"

class CAMERA_MODELS(Enum):
    """
    Camera models supported by PiKite, values returned represent the sensor model used by each model
    
    V1:
        Raspberry Pi Camera Module v1 (OV5647),
    V2:
        Raspberry Pi Camera Module v2 (IMX219),
    V3:
        Raspberry Pi Camera Module 3 (IMX708),
    HQ:
        Raspberry Pi HQ Camera (IMX477)

    See https://www.raspberrypi.com/documentation/accessories/camera.html#camera-module-specifications for more details
    """

    V1 = "OV5647"  # Raspberry Pi Camera Module v1
    V2 = "IMX219"  # Raspberry Pi Camera Module v2
    V3 = "IMX708"  # Raspberry Pi Camera Module 3
    HQ = "IMX477"  # Raspberry Pi HQ Camera

MAX_RESOLUTIONS = {
    CAMERA_MODELS.V1: {CAPTURE_MODES.STILL: (2592, 1944), CAPTURE_MODES.VIDEO: (1920, 1080)},
    CAMERA_MODELS.V2: {CAPTURE_MODES.STILL: (3280, 2464), CAPTURE_MODES.VIDEO: (1920, 1080)},
    CAMERA_MODELS.V3: {CAPTURE_MODES.STILL: (4608, 2592), CAPTURE_MODES.VIDEO: (1920, 1080)},
    CAMERA_MODELS.HQ: {CAPTURE_MODES.STILL: (4056, 3040), CAPTURE_MODES.VIDEO: (1920, 1080)}
}

class MEDIA_EXTENSIONS(str, Enum):
    """
    Supported media file extensions for photos and videos
    """
    JPG = ".jpg"
    PNG = ".png"
    MP4 = ".mp4"

    def __str__(self):
        return self.value
    
class DISTANCE_UNITS(str, Enum):
    """
    Supported distance units for altitude measurement
    """
    FEET = "feet"
    METERS = "meters"
    YARDS = "yards"
    MILES = "miles"
    KILOMETERS = "kilometers"
    CENTIMETERS = "centimeters"
    MILLIMETERS = "millimeters"