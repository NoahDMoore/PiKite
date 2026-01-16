"""
Menu class for PiKite
This class handles the menu system for the PiKite project, allowing navigation through different menu states,
executing actions, and updating the display based on the current menu state.
"""
from pathlib import Path
import xml.etree.ElementTree as ET

from core.constants import XMLTAG, XMLATTRIB, MENUACTION
from core.logger import get_logger
from core.settings import Settings
from hardware.display_controller import DisplayController, display_system_info
from system import power_management
from system.storage import StorageManager

# Setup Logger
logger = get_logger(__name__)

# Base Directory of PiKite Project
storage_manager = StorageManager()
MENU_FILE = storage_manager.MENU_FILE

class MenuElement:
	"""
	Represents a single element in the menu structure.
	Attributes:
		element (ET.Element): The XML element representing the menu item.
		tag (str): The tag of the XML element.
		name (str): The name attribute of the menu item.
		message (str): The message attribute of the menu item.
		action (str): The action attribute of the menu item.
		parent (MenuElement): The parent MenuElement, if any.
		value (str | None): The value associated with the menu item, if any.
		setting (str | None): The setting associated with the menu item, if any.
		options (list[MenuElement] | None): List of option MenuElements if action is 'option'.
		submenu (list[MenuElement] | None): List of submenu MenuElements if action is 'menu' or 'submenu'.
	"""
	def __init__(self, element: ET.Element, parent: "MenuElement | None"=None):
		"""
		Initializes a MenuElement instance.
		
		Args:
			element (ET.Element): The XML element representing the menu item.
			parent (MenuElement | None): The parent MenuElement, if any. Defaults to None.
		"""
		self.element = element	# ElementTree Object
		self.tag = self.element.tag
		self.name = self.element.attrib.get("name", f"Tag: {self.tag}")
		self.message = self.element.attrib.get("message", f"Tag: {self.tag}")
		self.action = self.element.attrib.get("action", "pass")
		self.parent = parent if parent is not None else self
		self.value = self.element.attrib.get(XMLATTRIB.VALUE, None)

		# Check for 'setting' element and get setting text if it exists
		setting_elem = self.element.find(XMLTAG.SETTING)
		if setting_elem is not None:
			self.setting = setting_elem.text
		else:
			self.setting = None
		
		# If element action is 'option', parse child 'option_item' elements
		if self.action == MENUACTION.OPTIONS:
			option_item_elems = self.element.findall(XMLTAG.OPTION_ITEM)
		else:
			option_item_elems = None
		self.options = [MenuElement(option, parent=self) for option in option_item_elems] if option_item_elems is not None else None

		# If element action is 'menu' or 'submenu', parse child 'menu_item' elements
		if self.tag == XMLTAG.MENU or self.action == MENUACTION.SUBMENU:
			menu_item_elems = self.element.findall(XMLTAG.MENU_ITEM)
		else:
			menu_item_elems = None
		self.submenu = [MenuElement(menu_item, parent=self) for menu_item in menu_item_elems] if menu_item_elems is not None else None

	def __repr__(self):
		return f"<{self.tag} name={self.name}, self.message={self.message}, action={self.action}, parent_name={self.parent.name}>"

	def __str__(self):
		return f"<{self.tag} name={self.name}, self.message={self.message}, action={self.action}, parent_name={self.parent.name}>"


class Menu:
	"""
	Manages the menu system for PiKite, allowing navigation and execution of various functions.

	Attributes:
		root (MenuElement): The root menu element parsed from the menu structure in an XML file.
		current_element (MenuElement): The currently selected menu element.
		default_element (MenuElement): The default menu element to reset to.
		previous_element (MenuElement): The previous menu element in the current context.
		next_element (MenuElement): The next menu element in the current context.
		display_controller (DisplayController): Instance of DisplayController to manage display output.
		settings (Settings): Instance of Settings to manage application settings.
	"""
	def __init__(self, display_controller: DisplayController, settings: Settings, menu_file: Path=MENU_FILE):
		"""
		Initializes the Menu instance by loading the menu structure from an XML file.
		
		Args:
			display_controller (DisplayController): Instance of DisplayController to manage display output.
			settings (Settings): Instance of Settings to manage application settings.
			menu_file (Path): Path to the XML file defining the menu structure.
							  Defaults to utils.StorageManager.MENU_FILE

		Raises:
			AssertionError: If the root menu does not contain any submenu items.
		"""
		self.root = MenuElement(ET.parse(MENU_FILE).getroot())
		try:
			assert self.root.submenu is not None, "Root menu must not be empty"
		except AssertionError as e:
			logger.critical(e)
			raise
		self.current_element = self.root.submenu[0]
		self.default_element = self.current_element
		self.update_menu()

		self.display_controller = display_controller
		self.settings = settings

	def __repr__(self):
		return f"<Current Menu Element: {self.current_element}>"

	def __str__(self):
		"""Returns the message of the current menu element."""
		return f"{self.current_element.message}>"	# Prints element message
	
	def update_menu(self):
		"""Update the menu state, including adjacent elements, and display it."""
		self._get_adjacent_elements()
		self._print_menu()

	def _get_adjacent_elements(self):
		"""Sets the previous_element and next_element properties based on the current element's context."""
		parent_element_options = self.current_element.parent.options
		if self.current_element.tag == XMLTAG.OPTION_ITEM and parent_element_options is not None:
			current_index = parent_element_options.index(self.current_element)
			max_index = len(parent_element_options) - 1
			self.previous_element = parent_element_options[current_index - 1]
			self.next_element = parent_element_options[current_index + 1] if current_index != max_index else parent_element_options[0]
			return
		
		parent_element_submenu = self.current_element.parent.submenu
		if parent_element_submenu is not None:
			current_index = parent_element_submenu.index(self.current_element)
			max_index = len(parent_element_submenu) - 1
			self.previous_element = parent_element_submenu[current_index - 1]
			self.next_element = parent_element_submenu[current_index + 1] if current_index != max_index else parent_element_submenu[0]
			return

	def _print_menu(self):
		"""Print the current menu message on the display"""
		self.display_controller.print_message(self.current_element.message)
		logger.debug(f"Menu Updated: {self.current_element}")

	def increment_element(self):
		"""Increment the current menu element to the next one in the list."""
		self.current_element = self.next_element
		self.update_menu()

	def decrement_element(self):
		"""Decrement the current menu element to the previous one in the list."""
		self.current_element = self.previous_element
		self.update_menu()

	def reset(self):
		"""Reset the menu to the default element."""
		self.current_element = self.default_element

	def do_action(self):
		"""Execute the action associated with the current menu element."""
		match self.current_element.action:
			case MENUACTION.SUBMENU:
				if self.current_element.submenu is not None:
					self.current_element = self.current_element.submenu[0]
				else:
					logger.error(f"'Submenu' action called, but no submenu exists for element: {self.current_element}")
					return
			case MENUACTION.OPTIONS:
				if self.current_element.options is not None and self.current_element.setting is not None:
					current_setting = self.settings.get(self.current_element.setting)
					self.current_element = next((option for option in self.current_element.options if option.value == current_setting), self.current_element)
				else:
					logger.error(f"'Options' action called, but no options and/or setting exists for element: {self.current_element}")
					return
			case MENUACTION.SELECT_OPTION:
				self.settings.set(self.current_element.parent.setting, self.current_element.value)
				self.current_element = self.current_element.parent
			case MENUACTION.RETURN:
				self.current_element = self.current_element.parent
			case MENUACTION.LOAD_DEFAULTS:
				self.settings.load_defaults()
				self.reset()
			case MENUACTION.DISPLAY_SYSTEM_INFO:
				display_system_info(self.display_controller)
			case MENUACTION.SHUTDOWN:
				power_management.shutdown()
			case MENUACTION.REBOOT:
				power_management.reboot()
			case _:
				logger.warning(f"No action defined for menu element: {self.current_element}")
				return
		
		self.update_menu()