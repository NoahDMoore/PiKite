import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.core.lcd_menu import Menu
from pikite.core.settings import Settings
from pikite.hardware.display_controller import DisplayController

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
    menu.increment_element()
    logger.info(f"Successfully incremented menu")
    logger.info(f"Current Menu Element Name: {menu.current_element.name}")
    time.sleep(2)
    menu.increment_element()
    logger.info(f"Successfully incremented menu")
    logger.info(f"Current Menu Element Name: {menu.current_element.name}")
    time.sleep(2)
    menu.increment_element()
    logger.info(f"Successfully incremented menu")
    logger.info(f"Current Menu Element Name: {menu.current_element.name}")
    time.sleep(2)
    menu.increment_element()
    logger.info(f"Successfully incremented menu")
    logger.info(f"Current Menu Element Name: {menu.current_element.name}")
    time.sleep(2)
    menu.increment_element()
    logger.info(f"Successfully incremented menu")
    logger.info(f"Current Menu Element Name: {menu.current_element.name}")
    time.sleep(2)
    menu.decrement_element()
    logger.info(f"Successfully decremented menu")
    logger.info(f"Current Menu Element Name: {menu.current_element.name}")
    time.sleep(2)
    menu.decrement_element()
    logger.info(f"Successfully decremented menu")
    logger.info(f"Current Menu Element Name: {menu.current_element.name}")

    # Simulate navigating to the first submenu if available
    if initial_element.submenu:
        menu.do_action()
        new_element = menu.current_element
        logger.info(f"Navigated to Submenu Element: {new_element.name}")
        assert new_element != initial_element
    else:
        logger.warning("No submenu available to navigate to in the initial element")