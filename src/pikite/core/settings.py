import ast
import configparser
from pathlib import Path
from typing import Any

from core.logger import get_logger
from system.storage import StorageManager

# Setup Logger
logger = get_logger(__name__)

# File Paths
storage = StorageManager()
CONFIG_FILE  = storage.CONFIG_FILE                  # Settings file for PiKite
DEFAULT_CONFIG_FILE  = storage.DEFAULT_CONFIG_FILE  # Default settings file for PiKite

# Map of setting prefixes to sections
# This allows us to determine which section a setting belongs based on its prefix
PREFIX_SECTION_MAP = {
    # Prefix : Section
    "alt": "altitude_settings",
    "cam": "camera_settings",
    "pic": "photo_settings",
    "vid": "video_settings",
    "pan": "pan_tilt_settings",
    "log": "logging_settings",
}

class Settings:
    """
    A class to manage application settings using a configuration file.
    """
    def __init__(self, config_path: Path = CONFIG_FILE, default_path: Path = DEFAULT_CONFIG_FILE):
        """
        Initialize the Settings object.
        
        Args:
            config_path (Path): Path to the configuration file.
            default_path (Path): Path to the default configuration file.
        """
        self.config_path = config_path
        self.default_path = default_path

        if not self.config_path.exists():
            logger.error((f"Config File Not Found: {self.config_path}. Creating from default settings."))
            self.load_defaults(read_after=False)

        self.config = configparser.ConfigParser()
        self.config.read(self.config_path)

    def get(self, setting_key: str, default: Any=None) -> Any:
        """
        Retrieves the value for a given setting key from the configuration file.
        
        Args:
            setting_key (str): The key of the setting to retrieve.
            default (Any, optional): The default value to return if the setting is not found. Defaults to None.
        
        Returns:
            Any: The value of the setting, or the default value if not found.

        Raises:
            KeyError: If the setting is not found and no default is provided. Returns None in this case.
        """
        section = get_section(setting_key)
        if section not in self.config or setting_key not in self.config[section]:
            try:
                raise KeyError(f"Setting '{setting_key}' not found in section '{section}'")
            except KeyError as e:
                logger.error(f"{e}. Returning default value: {default}")
                return default
            
        return ast.literal_eval(self.config[section][setting_key])    # Returns value stored for a given setting_key

    def set(self, setting_key, value):
        """
        Sets the value for a given setting key in the configuration file.
        Args:
            setting_key (str): The key of the setting to set.
            value (Any): The value to set for the setting.
        
        Raises:
            ValueError: If the setting_key does not correspond to a known section.
        """
        section = get_section(setting_key)
        self.config[section][setting_key] = str(value)
        with open(self.config_path, "w") as configfile:
            self.config.write(configfile)

    def load_defaults(self, read_after=True):
        """
        Load default settings from the default configuration file.
        
        Args:
            read_after (bool): Whether to read the config file after loading defaults. Defaults to True.
            
        Raises:
            FileNotFoundError: If the default configuration file does not exist.
        """
        if not self.default_path.exists():
            try:
                raise FileNotFoundError(f"Default config file not found: {self.default_path}")
            except FileNotFoundError as e:
                logger.critical(e)
                raise
        with open(self.default_path, "r") as src, open(self.config_path, "w") as dst:
            dst.write(src.read())

        if read_after:
            self.config.read(self.config_path)

# Function to get the section for a given setting
def get_section(setting_key: str) -> str:
    """
    Determine the section of the configuration file for a given setting key.

    Args:
        setting_key (str): The key of the setting.
    
    Returns:
        str: The section name where the setting is located.

    Raises:
        ValueError: If the setting_key does not correspond to a known section.
    """
    for prefix, section in PREFIX_SECTION_MAP.items():
        if setting_key.startswith(prefix):
            return section
    
    try:
        raise ValueError(f"""Key does not correspond a known section: {setting_key}. \n
                        Ensure key is properly prefixed (See: core.settings.PREFIX_SECTION_MAP)""")
    
    except ValueError as e:
        logger.error(e)
        raise