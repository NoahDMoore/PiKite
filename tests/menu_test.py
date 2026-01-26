import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.input_handler import InputHandler, InputCommand
from pikite.core.logger import get_logger
from pikite.core.lcd_menu import Menu
from pikite.core.settings import Settings
from pikite.hardware.display_controller import DisplayController
from pikite.hardware.button_controller import ButtonController

import time

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting Menu Tests")

def test_menu_initialization():
    settings = Settings()
    display_controller = DisplayController()
    menu = Menu(display_controller, settings)
    assert menu is not None
    logger.info("Menu initialized successfully")

def test_menu_navigation():
    settings = Settings()
    display_controller = DisplayController()
    menu = Menu(display_controller, settings)

    initial_element = menu.current_element
    logger.info(f"Initial Menu Element: {initial_element.name}")

    time.sleep(2)

    # Increment and Decrement the menu
    for i in range(5):
        menu.increment_element()
        logger.info(f"Successfully incremented menu")
        logger.info(f"Current Menu Element Name: {menu.current_element.name}")
        time.sleep(2)

    for i in range(2):    
        menu.decrement_element()
        logger.info(f"Successfully decremented menu")
        logger.info(f"Current Menu Element Name: {menu.current_element.name}")
        time.sleep(2)

    # Simulate navigating to the first submenu if available
    current_element = menu.current_element
    if current_element.submenu:
        menu.do_action()
        new_element = menu.current_element
        logger.info(f"Navigated to Submenu Element: {new_element.name}")
        assert new_element != current_element
    else:
        logger.warning("No submenu available to navigate to in the initial element")

def test_menu_navigation_with_buttons():
    logger.info("Testing menu navigation with button presses")

    settings = Settings()
    display_controller = DisplayController()
    menu = Menu(display_controller, settings)
    logger.info("Menu initialized for button navigation test")

    input_handler = InputHandler()
    input_handler.set_scope("MENU")
    input_handler.register(
        scope="MENU",
        command=InputCommand.NEXT,
        callback=menu.increment_element
    )

    input_handler.register(
        scope="MENU",
        command=InputCommand.PREVIOUS,
        callback=menu.decrement_element
    )

    input_handler.register(
        scope="MENU",
        command=InputCommand.SELECT,
        callback=menu.do_action
    )

    logger.info("InputHandler configured for menu navigation")

    with ButtonController(input_handler, pin_next=24, pin_select=23, pull_up=True, debounce_ms=200) as button_controller:
        logger.info("ButtonController initialized for menu navigation test")
        logger.info("Press the NEXT and SELECT buttons to navigate the menu. Test will run for 20 seconds.")
        start_time = time.time()
        while time.time() - start_time < 20:
            time.sleep(0.1)