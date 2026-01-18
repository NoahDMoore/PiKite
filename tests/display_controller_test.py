import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.hardware.display_controller import DisplayController, LoadingBar, PreLoader

import time

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting DisplayController Tests")

def test_display_controller_initialization():
    display_controller = DisplayController()
    assert display_controller is not None
    logger.info("DisplayController initialized successfully")

def test_display_clear():
    display_controller = DisplayController()
    display_controller.clear()
    logger.info("DisplayController cleared successfully")

def test_new_image():
    display_controller = DisplayController()
    image, canvas = display_controller.new_image()
    assert image is not None
    assert canvas is not None
    logger.info("New image and canvas created successfully")

def test_backlight_control():
    display_controller = DisplayController()
    display_controller.backlight_on()
    logger.info("Backlight turned on successfully")
    time.sleep(5)
    display_controller.backlight_off()
    logger.info("Backlight turned off successfully")
    time.sleep(5)
    display_controller.backlight_on()
    logger.info("Backlight turned on successfully")

def test_print_one_line_message():
    display_controller = DisplayController()
    display_controller.print_message("Hello, PiKite!")
    logger.info("Message printed successfully on DisplayController")

def test_print_two_line_message():
    display_controller = DisplayController()
    display_controller.print_message("Header: This is a test.")
    logger.info("Two-line message printed successfully on DisplayController")

def test_loading_bar():
    display_controller = DisplayController()
    loading_bar = LoadingBar("Loading Test", display_controller)
    logger.info("Loading bar displayed successfully on DisplayController")
    time.sleep(2)
    while loading_bar.percentage < 100:
        loading_bar.advance()
        time.sleep(0.5)
    logger.info("Loading bar completed successfully on DisplayController")

def test_preloader_gif():
    display_controller = DisplayController()
    preloader = PreLoader(display_controller)
    logger.info("Preloader GIF initialized successfully on DisplayController")
    time.sleep(2)
    preloader.play()
    logger.info("Preloader GIF played successfully on DisplayController")