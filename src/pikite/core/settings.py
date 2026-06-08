import ast
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable
import yaml

from pikite.utils.logger import get_logger
from pikite.system.storage import StorageManager

# Setup Logger
logger = get_logger(__name__)

# File Paths
storage = StorageManager()
CONFIG_FILE  = storage.CONFIG_FILE # Settings file for PiKite
DEFAULT_CONFIG_FILE = storage.DEFAULT_CONFIG_FILE # Default settings file for PiKite

type_mapping = {
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "tuple": tuple,
    "str": str
}

class Settings:
    """
    A class to manage application settings using a YAML configuration file.
    """
    def __init__(self, config_path: Path = CONFIG_FILE):
        """
        Initialize the Settings object.
        
        Args:
            config_path (Path): Path to the YAML configuration file.
        """
        self.config_path = config_path
        self.config = {}
        self._setting_change_listeners = []

        if not self.config_path.exists():
            logger.error((f"Config File Not Found: {self.config_path}. Creating default configuration file."))
            self._create_default_config()

        self._load_config()

    def _load_config(self):
        """Load the YAML configuration file into a dictionary."""
        try:
            with open(self.config_path, 'r', encoding="utf-8") as f:
                self.config = yaml.load(f, Loader=yaml.SafeLoader)
                logger.info(f"Settings loaded successfully from {self.config_path}")
        except Exception as e:
            logger.error(f"Failed to load settings from {self.config_path}: {e}")
            raise e

    def _create_default_config(self):
        """Create a default YAML configuration file from the default settings."""
        try:
            with open(DEFAULT_CONFIG_FILE, 'r', encoding="utf-8") as f:
                default_config = yaml.load(f, Loader=yaml.SafeLoader)
                
                with open(self.config_path, 'w', encoding="utf-8") as f:
                    yaml.dump(default_config, f, sort_keys=False)
                logger.info(f"Default configuration file created at {self.config_path}")
        except FileNotFoundError as e:
            logger.critical(f"Default config file not found at {DEFAULT_CONFIG_FILE}. Cannot create config file.")
            raise e
        except Exception as e:
            logger.error(f"Failed to create default config file at {self.config_path}: {e}")
            raise e
    
    def _get_setting_node(self, setting_key: str, get_copy: bool = False) -> dict:
        """
        Retrieves the dictionary node for a given setting key from the configuration.

        Args:
            setting_key (str): The key of the setting to retrieve, in dot notation (e.g., "camera.cam_model")
            get_copy (bool): If True, returns a deep copy of the setting node with 'copy_of' and 'setting_key' injected into the node.
            
        Returns:
            dict: The dictionary node in the config for the given setting key.
        
        Raises:
            KeyError: If the given setting key is not a valid path in the config dictionary.
            ValueError: If the setting key exists in the config dictionary but does not point to a valid setting.
        """
        keys = setting_key.split('.')
        current_level = self.config

        for key in keys:
            if key not in current_level:
                raise KeyError(f"Setting key '{setting_key}' not found in configuration.")

            current_level = current_level[key]

        if current_level.get('type') != "setting":
            raise ValueError(f"Key '{setting_key}' exists but does not correspond to a valid setting.")

        if get_copy:
            current_level = deepcopy(current_level)
            current_level["copy_of"] = f"Setting '{setting_key}' in config of '{self.__repr__()}'"
            current_level["setting_key"] = setting_key

        return current_level

    def get(self, setting_key: str, default: Any=None) -> Any:
        """
        Retrieves the value for a given setting key from the configuration.
        
        Args:
            setting_key (str): The key of the setting to retrieve, in dot notation (e.g., "camera_settings.resolution").
            default (Any, optional): The default value to return if the setting is not found. Defaults to None.

        Returns:
            Any: The value of the setting, or the default value if not found.

        Raises:
            TypeError: The data_type for the given setting does not map to a valid data type.
        """
        try:
            setting = self._get_setting_node(setting_key)
        except Exception as e:
            logger.error(f"{e} Returning default: {default}")
            return default

        value = setting.get('current_value', default)
        data_type_key = setting.get("data_type", "")
        data_type = type_mapping.get(data_type_key)

        if not data_type:
            logger.error(f"Setting '{setting_key}' has unknown data_type '{data_type_key}'. Returning default: {default}")
            return default

        if isinstance(value, data_type):
            return value

        if data_type is tuple and isinstance(value, str):
            try:
                return ast.literal_eval(value)
            except (ValueError, SyntaxError) as e:
                logger.error(f"Failed to parse tuple string for '{setting_key}': {e}. Returning default: {default}")
                return default

        logger.error(f"Could not coerce value '{value}' to type '{data_type.__name__}' for setting '{setting_key}'. Returning default: {default}")
        return default

    def _normalize_option(self, option: Any) -> dict:
        if isinstance(option, dict):
            if "label" in option and "value" in option and "display_message" in option:
                return {
                    "label": option["label"],
                    "value": option["value"],
                    "display_message": option["display_message"]
                }
            
            if "label" in option and "value" in option:
                return {
                    "label": option["label"],
                    "value": option["value"],
                    "display_message": f"[{option['label']}]"
                }

            if len(option) == 1:
                label, value = next(iter(option.items()))
                return {
                    "label": str(label),
                    "value": value,
                    "display_message": f"[{str(label)}]"
                }

            return {
                "label": option.get("label", str(option)),
                "value": option.get("value", option),
                "display_message": f"[{option.get('label', str(option))}]"
            }

        return {
            "label": str(option),
            "value": option,
            "display_message": f"[{str(option)}]"
        }

    def _build_explicit_options(self, options: list[Any]) -> list[dict]:
        return [self._normalize_option(option) for option in options]

    def _build_range_options(self, options: dict) -> list[dict]:
        minimum = options["min"]
        maximum = options["max"]
        step = options.get("step", 1)

        if not isinstance(step, (int, float)) or step == 0:
            step = 1

        normalized_options: list[dict] = []
        value = minimum
        while value <= maximum:
            label = f"{value} {options['unit']}" if "unit" in options else str(value)
            normalized_options.append({
                "label": label,
                "value": value,
                "display_message": f"[{label}]"
            })
            value += step

        return normalized_options

    def _rotate_options(self, normalized_options: list[dict], current_value: Any):
        if current_value is None:
            yield from normalized_options
            return

        current_index = None
        for index, option in enumerate(normalized_options):
            if option["value"] == current_value or str(option["value"]) == str(current_value):
                current_index = index
                normalized_options[index]["display_message"] += " (Current)"
                break

        if current_index is None:
            yield from normalized_options
            return

        yield normalized_options[current_index]
        for option in normalized_options[current_index + 1:]:
            yield option
        for option in normalized_options[:current_index]:
            yield option

    def iter_valid_options(self, setting_key: str):
        """
        Yield valid option entries for the specified setting.

        The current value is yielded first, followed by all other valid options.
        Each yielded option is a dict with at least 'value' and 'label'.
        """
        setting = self._get_setting_node(setting_key, get_copy=True)
        options = setting.get("options")
        if options is None:
            if type_mapping.get(setting.get("data_type", "")) == bool:
                options = [
                    {
                        "label": "True",
                        "value": True,
                        "display_message": "[Yes]     No"
                    },
                    {
                        "label": "False",
                        "value": False,
                        "display_message": "Yes     [No]"
                    },
                ]
            else:
                return

        current_value = setting.get("current_value")
        if isinstance(options, list):
            normalized_options = self._build_explicit_options(options)
        elif isinstance(options, dict) and "min" in options and "max" in options:
            normalized_options = self._build_range_options(options)
        else:
            logger.error(f"Invalid options format for setting '{setting_key}'. Expected list or range dict.")
            return

        yield from self._rotate_options(normalized_options, current_value)

    def get_valid_options(self, setting_key: str) -> list[dict]:
        """
        Return a concrete list of valid options for the setting.
        """
        return list(self.iter_valid_options(setting_key))
    
    def iter_cyclic_options(self, setting_key):
        options = self.get_valid_options(setting_key)
        if not options:
            return
        index = 0
        while True:
            yield options[index]
            index = (index + 1) % len(options)

    def validate_option(self, setting_key: str, value: Any) -> bool:
        """
        Validate that a value is a valid option for the given setting.
        If the setting has no options defined, returns True (no constraint).
        """
        try:
            valid_options = self.get_valid_options(setting_key)
            if not valid_options:
                return True  # No options to validate against, so any value is valid
            
            for option in valid_options:
                if option["value"] == value or str(option["value"]) == str(value):
                    return True
            
            # Value not found - provide context-specific logging
            setting_node = self._get_setting_node(setting_key)
            options_def = setting_node.get("options")
            setting_label = setting_node.get("label", setting_key)
            
            if isinstance(options_def, list):
                logger.info(f"Value '{value}' does not match a valid option in setting '{setting_label}'.")
            elif isinstance(options_def, dict) and "min" in options_def and "max" in options_def:
                minimum = options_def["min"]
                maximum = options_def["max"]
                logger.info(f"Value '{value}' is not in the valid range [{minimum}, {maximum}] for setting '{setting_label}'.")
            
            return False
        except Exception as e:
            logger.error(f"Error validating option for setting '{setting_key}': {e}")
            return False

    def set(self, setting_key: str, new_value: Any):
        """
        Sets the value for a given setting key (in dot notation) in the configuration file.

        Args:
            setting_key (str): The key of the setting to set.
            new_value (Any): The new value for the setting.
        
        Raises:
            ValueError: If the setting_key is not a valid setting.
            ValueError: If the setting_key does not correspond to a known section.
        """
        try:
            setting = self._get_setting_node(setting_key)
        except (KeyError, ValueError) as e:
            logger.error(e)
            return
        
        current_value = setting.get('current_value')
        setting_data_type = type_mapping.get(setting["data_type"])

        if not setting_data_type:
            logger.error(f"Failed to update '{setting_key}'. Unknown data_type '{setting.get('data_type')}'.")
            return

        if current_value == new_value:
            logger.info(f"Setting '{setting_key}' is already set to the desired value: {new_value}. No change made.")
            return
        
        # Validate Data Type
        if not isinstance(new_value, setting_data_type):
            logger.error(f"Failed to update '{setting_key}'. Provided value '{new_value}' does not match data type '{setting_data_type.__name__}'.")
            return
        
        # Validate Value Against Options
        if not self.validate_option(setting_key, new_value):
            logger.error(f"Failed to update '{setting_key}'. Provided value '{new_value}' is not a valid option.")
            return

        setting["current_value"] = new_value

        with open(self.config_path, 'w', encoding="utf-8") as f:
            yaml.dump(self.config, f, sort_keys=False)
            logger.info(f"Setting updated: {setting_key} = {new_value}")
        
        self._load_config()

        self._notify_change_listeners(setting_key, new_value)

    def update_from_dict(self, settings_to_update: dict[str, str]):
        """
        Update multiple settings from key, value pairs in a dictionary.
        
        Args:
            settings_to_update (dict[setting_key, value]): The settings to update.
        """
        if not isinstance(settings_to_update, dict):
            logger.error(f"Error updating settings. Settings must be provided as a dictionary of setting key and value pairs.")

        for key, value in settings_to_update.items():
            self.set(key, value)

    def load_defaults(self, read_after=True):
        """
        Load default settings from the default configuration file.
        
        Args:
            read_after (bool): Whether to read the config file after loading defaults. Defaults to True.
            
        Raises:
            FileNotFoundError: If the default configuration file does not exist.
        """
        def _recursively_restore_defaults(node):
            for value in node.values():
                if not isinstance(value, dict):
                    continue

                if not value.get("type") == "setting":
                    _recursively_restore_defaults(value)
                    continue

                default_value = value["default"]
                value["current_value"] = default_value

        _recursively_restore_defaults(self.config)

        with open(self.config_path, 'w', encoding="utf-8") as f:
            yaml.dump(self.config, f, sort_keys=False)

        if read_after:
            self._load_config()

    def add_change_listener(self, callback: Callable):
        """
        Add a callback function that will be run whenever a setting is changed.
        
        Args:
            callback (callable): A function that takes two arguments (setting_key, new_value) and will be called on setting changes.
        """
        if callable(callback):
            self._setting_change_listeners.append(callback)
            logger.info(f"Added new setting change listener: {callback}")
        else:
            logger.error(f"Attempted to add non-callable setting change listener: {callback}")

    def _notify_change_listeners(self, setting_key, new_value):
        """
        Notify all registered change listeners of a setting change.
        
        Args:
            setting_key (str): The key of the setting that changed.
            new_value (Any): The new value of the setting.
        """
        for callback in self._setting_change_listeners:
            try:
                callback(setting_key, new_value)
                logger.info(f"Notified listener {callback} of setting change: {setting_key} = {new_value}")
            except Exception as e:
                logger.error(f"Error notifying listener {callback} of setting change: {e}")