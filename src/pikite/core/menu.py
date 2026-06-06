"""
Menu class for PiKite
This class handles the menu system for the PiKite project, allowing navigation through different menu states,
executing actions, and updating the display based on the current menu state.
"""
from __future__ import annotations 
import ast
from pathlib import Path
import yaml

from .input_handler import InputHandler, InputCommand, InputSource
from ..utils.logger import get_logger
from .settings import Settings

# Mock hardware controller class for testing on non-RPi system; remove when done testing
try:
    from ..hardware.display_controller import DisplayController  # type: ignore
except Exception:
    class DisplayController:
        """
        Placeholder DisplayController class for type hinting. Replace with actual implementation.
        """
        def print_message(self, message: str):
            print(f"Display Message: {message}")

from ..system.storage import StorageManager

# Setup Logger
logger = get_logger(__name__)

# Base Directory of PiKite Project
storage_manager = StorageManager()
MENU_FILE = storage_manager.MENU_FILE

class MenuElement:
    """
    Represents a single element in the menu structure.
    """

    def __init__(
        self,
        element_dict: dict,
        app_settings: Settings,
        parent: MenuElement | None = None,
        element_path: str | None = None
    ):
        self.dict = element_dict
        self.name = self.dict.get("label")
        self.type = self.dict.get("type")
        self.command = self.dict.get("command")
        self.command_params = self.dict.get("command_params")
        self.value = self.dict.get("value")
        self.setting_key = self.dict.get("setting_key")
        self.requires_confirmation = self.dict.get("requires_confirmation")
        self.parent = parent
        self.app_settings = app_settings
        self.element_path = element_path

        if self.setting_key is None and self.type == "setting" and self.element_path is not None:
            self.setting_key = self.element_path

        # Set the Display Message
        if self.dict.get("display_message"):
            self.display_message = self.dict.get("display_message")
        elif self.type == "image" and self.dict.get("file_name"):
            self.display_message = self.dict.get("file_name")
        else:
            self.display_message = self.dict.get("message", self.name)

        # If the element has a submenu, create the submenu level
        if self.type in ("submenu", "settings_menu", "settings_group"):
            self.submenu = self._get_submenu()
        else:
            self.submenu = None

    def __repr__(self):
        repr = []
        
        repr.append(f"MenuElement: <name={self.name}, type={self.type}, display_message={self.display_message}")
            
        if self.command is not None:
            repr.append(f", command={self.command}")

        if self.command_params is not None:
            repr.append(f", command_params={self.command_params}") 

        if self.value is not None:
            repr.append(f", value={self.value}")

        if self.setting_key is not None:
            repr.append(f", setting_key={self.setting_key}")

        if self.requires_confirmation is not None:
            repr.append(f", requires_confirmation={self.requires_confirmation}")
            
        if self.parent is not None:
            repr.append(f", parent={self.parent.name}")

        repr.append(f">")
        
        return "".join(repr)

    def _get_submenu(self):
        if self.type == "settings_menu":
            submenu_dict = self.app_settings.config
        else:
            submenu_dict = self.dict.get("submenu")

        match self.type:
            case "submenu":
                submenu_dict = self.dict.get("submenu")
            case "settings_menu":
                submenu_dict = self.app_settings.config
            case "settings_group":
                submenu_dict = {
                    k: v for k, v in self.dict.items() 
                    if k not in ("label", "description", "type") and isinstance(v, dict)
                }

        if isinstance(submenu_dict, dict):
            # On entering a settings_group element, start propogating the path down to the setting to track the setting_key
            if self.type == "settings_group":
                submenu_path = self.element_path or ""
            else:
                submenu_path = ""

            return MenuLevel(
                level_dict = submenu_dict,
                app_settings = self.app_settings,
                parent=self,
                submenu=True,
                path=submenu_path
            )
        
        return None

class MenuLevel:
    def __init__(
            self,
            level_dict: dict,
            app_settings: Settings,
            parent: MenuElement | None = None,
            submenu: bool = False,
            path: str = ""
        ):
        self.dict = level_dict
        self.parent = parent
        self.app_settings = app_settings
        self.path = path
        self.elements: list[MenuElement] = list(self._yield_elements())
        self.submenu = submenu

        self._index = 0

        if self.submenu:
            self._insert_return_element()

    def _yield_elements(self):
        for key, item in self.dict.items():
            element_path = f"{self.path}.{key}" if self.path else key
            yield MenuElement(
                element_dict = item,
                app_settings = self.app_settings,
                parent = self.parent,
                element_path = element_path
            )

    def _insert_return_element(self):
        if self.parent is None:
            parent_name = "Parent"
        else:
            parent_name = self.parent.name

        return_element_dict = {
            "label": f"Exit '{parent_name}'",
            "type": "return"
        }

        self.elements.append(
            MenuElement(
                element_dict = return_element_dict,
                app_settings = self.app_settings,
                parent = self.parent
            )
        )

    @property
    def current_element(self) -> MenuElement:
        return self.elements[self._index]
    
    @current_element.setter
    def current_element(self, element: MenuElement):
        self._index = self.elements.index(element)
        
    @property
    def previous_element(self) -> MenuElement:
        if self._index == 0:
            return self.elements[-1]
        else:
            return self.elements[self._index - 1]

    @property
    def next_element(self) -> MenuElement:
        if self._index == (len(self.elements) - 1):
            return self.elements[0]
        else:
            return self.elements[self._index + 1]
    
    def decrement(self):
        self.current_element = self.previous_element

    def increment(self):
        self.current_element = self.next_element

    def reset(self):
        """Reset current_element to the first element in the level"""
        self._index = 0

class Menu:
    """
    Manages the menu system for PiKite, allowing navigation and execution of various functions.
    """
    def __init__(self, display_controller: DisplayController | None, settings: Settings, input_handler: InputHandler | None, menu_file: Path=MENU_FILE):
        """
        Initializes the Menu instance by loading the menu structure from an XML file.
        
        Args:
            display_controller (DisplayController | None): Instance of DisplayController to manage display output.
            settings (Settings): Instance of Settings to manage application settings.
            input_handler (InputHandler | None): Instance of InputHandler to manage input commands.
            menu_file (Path): Path to the XML file defining the menu structure.
                              Defaults to utils.StorageManager.MENU_FILE
        """
        self.display_controller = display_controller
        self.app_settings = settings
        self.input_handler = input_handler

        self.menu_file = menu_file
        self.dict = self._load_menu(self.menu_file) # Load the menu yaml into self.menu
        self.root = MenuLevel(
            level_dict = self.dict,
            app_settings = self.app_settings
        )
        
        self.current_level = self.root
        self._ancestors: list[MenuLevel] = []

    def __repr__(self):
        return f"<Current Menu Element: {self.current_element}>"

    def __str__(self):
        """Returns the name of the current menu element."""
        return f"MenuElement: {self.current_element.name}>"
    
    @property
    def current_element(self):
        return self.current_level.current_element
    
    def _load_menu(self, menu_file) -> dict:
        """Load the YAML configuration file into a dictionary."""
        try:
            with open(menu_file, 'r') as f:
                menu_dict = yaml.load(f, Loader=yaml.SafeLoader)
                logger.info(f"Menu loaded successfully from {menu_file}")
                return menu_dict
        except Exception as e:
            logger.error(f"Failed to load menu from {menu_file}: {e}")
            raise e

    def update_menu(self):
        """Print the current menu message on the display"""
        message = self.current_element.display_message
        
        if message is None:
            message = "No Message Defined"
            logger.warning(f"No message defined for menu element: {self.current_element}")

        if ".jpg" in message or ".png" in message:
            message = str(storage_manager.MEDIA_DIR / message)
        
        if self.display_controller is None:
            logger.warning("No display controller available to print menu message")
            return
        else:
            self.display_controller.print_message(message)
        
        logger.debug(f"Menu Updated: {self.current_element.name}")

    def decrement(self):
        """Decrement the current menu element to the previous one in the list."""
        self.current_level.decrement()
        self.update_menu()

    def increment(self):
        """Increment the current menu element to the next one in the list."""
        self.current_level.increment()
        self.update_menu()

    def enter_submenu(self):
        if self.current_element.submenu is None:
            logger.error(f"Cannot enter submenu. Current element '{self.current_element.name}' does not have a submenu.")
            return

        self._ancestors.append(self.current_level)
        self.current_element.submenu.reset()
        self.current_level = self.current_element.submenu
        self.update_menu()

    def return_to_parent(self):
        if self.current_element.parent is None:
            logger.error(f"Cannot return to parent element. Current element '{self.current_element.name}' does not have a parent or is already at the root level.")
            return
        
        parent_level = self._ancestors.pop()
        self.current_level = parent_level
        self.update_menu()

    def reset(self):
        """Reset the menu to the default element."""
        self.current_level = self.root
        self.root.reset()

    def do_action(self):
        match self.current_element.type:
            case "submenu":
                self._handle_submenu_action()
            case "settings_menu":
                self._handle_submenu_action()
            case "settings_group":
                self._handle_submenu_action()
            case "return":
                self.return_to_parent()
            case "input_command":
                self._handle_command()
            case "confirm_input_command":
                self._handle_command()
                self.return_to_parent()
            case "setting":
                self._get_options()
            case "setting_option":
                self._update_setting()
                self.return_to_parent()
            case "image":
                self.update_menu()
            case _:
                logger.error(f"Error executing action for element '{self.current_element.name}'. Could not match type '{self.current_element.type}' to a valid action.")
                return

    def _handle_submenu_action(self):
        if self.current_element.submenu is not None:
            self.enter_submenu()
        else:
            logger.error(f"'Submenu' action called, but no submenu exists for element: {self.current_element}")

    def _handle_command(self):
        command_name = self.current_element.command
        
        if command_name is None:
            logger.error(f"Error executing action. No command was provided for element '{self.current_element.name}' of type '{self.current_element.type}'")
            return
        
        if self.current_element.requires_confirmation:
            self._await_confirmation(command_name)
            return

        if self.input_handler is None:
            logger.error("Error executing action. No input handler available.")
            return
        
        logger.debug(f"Handling input command for menu element: {self.current_element}")

        try:
            command = InputCommand[command_name]  # expect enum NAME like START_CAPTURE
        except KeyError:
            logger.error(f"Error executing action. Unknown InputCommand: {command_name}")
            return

        # Handle the input command via the input handler
        self.input_handler.handle(command=command, source=InputSource.MENU)

    def _await_confirmation(self, command_name):
        confirmation_level_dict = {
            "deny": {
                "label": "Deny",
                "display_message":  "Really? [No]",
                "type": "return",
            },

            "confirm": {
                "label": "Confirm",
                "display_message": "Really? [Yes]",
                "type": "confirm_input_command",
                "command": command_name
            }
        }

        confirmation_submenu = MenuLevel(
            level_dict = confirmation_level_dict,
            app_settings = self.app_settings,
            parent = self.current_element
        )

        self._ancestors.append(self.current_level)
        self.current_level = confirmation_submenu
        self.update_menu()

    def _get_options(self):
        if self.current_element.type != "setting":
            logger.error(f"Error getting options for element '{self.current_element.name}'. Element type '{self.current_element.type}' is not 'settings'.")
            return

        if self.current_element.setting_key is None:
            logger.error(f"Error getting options for element '{self.current_element.name}'. No setting key provided.")
            return
        
        valid_options = self.app_settings.get_valid_options(self.current_element.setting_key)

        options_level_dict = {}

        for option in valid_options:
            option["type"] = "setting_option"
            option["setting_key"] = self.current_element.setting_key

            options_level_dict[option["label"]] = option

        options_submenu = MenuLevel(
            level_dict = options_level_dict,
            app_settings = self.app_settings,
            parent = self.current_element
        )

        self._ancestors.append(self.current_level)
        self.current_level = options_submenu
        self.update_menu()

    def _update_setting(self):
        if self.current_element.type != "setting_option":
            logger.error(f"Cannot update settings. Current element is not a valid setting option.")
            return

        if self.current_element.setting_key is None:
            logger.error(f"Cannot update settings. No setting key provided.")
            return

        self.app_settings.set(self.current_element.setting_key, self.current_element.value)