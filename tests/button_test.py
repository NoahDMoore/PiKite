import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.hardware.button_controller import ButtonController
from pikite.core.input_handler import InputHandler, InputCommand, InputSource

import time

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting Button/Input Tests")

def test_input_handler_initialization():
    input_handler = InputHandler()
    assert input_handler._active_scope == "default"
    logger.info("InputHandler initialized correctly")

def test_input_handler_scope_management():
    input_handler = InputHandler()
    input_handler.set_scope("test_scope")
    assert input_handler._active_scope == "test_scope"
    logger.info("InputHandler scope set correctly")

    input_handler.clear_scope("test_scope")
    assert "test_scope" not in input_handler._listeners
    logger.info("InputHandler scope cleared correctly")

def test_input_handler_registration_and_handling():
    input_handler = InputHandler()
    test_flag = {"called": False}

    def test_callback(**kwargs):
        test_flag["called"] = True
        logger.info("Test callback executed")

    input_handler.register("default", InputCommand.NEXT, test_callback)
    input_handler.handle(command=InputCommand.NEXT, source=InputSource.SYSTEM)

    assert test_flag["called"] is True
    logger.info("InputHandler registration and handling works correctly")

def test_button_controller_initialization_and_callbacks():
    input_handler = InputHandler()

    with ButtonController(input_handler, pin_next=24, pin_select=23, pull_up=True, debounce_ms=200) as button_controller:
        assert button_controller.pin_next == 24
        assert button_controller.pin_select == 23
        logger.info("ButtonController initialized correctly")

        # Simulate button presses by directly calling the callback methods
        test_flag = {"next_called": False, "select_called": False}

        def next_callback(**kwargs):
            test_flag["next_called"] = True
            logger.info("NEXT button callback executed")

        def select_callback(**kwargs):
            test_flag["select_called"] = True
            logger.info("SELECT button callback executed")

        input_handler.register("default", InputCommand.NEXT, next_callback)
        input_handler.register("default", InputCommand.SELECT, select_callback)

        # Simulate NEXT button press
        button_controller._on_next_pressed(channel=24)
        assert test_flag["next_called"] is True

        # Simulate SELECT button press
        button_controller._on_select_pressed(channel=23)
        assert test_flag["select_called"] is True

        logger.info("ButtonController callbacks work correctly")

    logger.info("ButtonController context exited and cleaned up correctly")

    assert True  # If we reach here, cleanup was successful

def test_real_button_presses():
    input_handler = InputHandler()

    with ButtonController(input_handler, pin_next=24, pin_select=23, pull_up=True, debounce_ms=200) as button_controller:
        logger.info("Press the NEXT and SELECT buttons to test callbacks.")

        next_pressed = False
        select_pressed = False

        def next_callback(**kwargs):
            next_pressed = True
            logger.info("NEXT button pressed!")

        def select_callback(**kwargs):
            select_pressed = True
            logger.info("SELECT button pressed!")

        input_handler.register("default", InputCommand.NEXT, next_callback)
        input_handler.register("default", InputCommand.SELECT, select_callback)

        logger.info("Waiting for NEXT button press...")
        time.sleep(20)
        assert next_pressed, "NEXT button was not pressed during the test period."

        logger.info("Waiting for SELECT button press...")
        time.sleep(20)
        assert select_pressed, "SELECT button was not pressed during the test period."

    logger.info("Finished real button press test")