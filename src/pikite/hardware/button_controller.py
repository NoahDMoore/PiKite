import RPi.GPIO as GPIO
from typing import Optional

from ..core.input_handler import InputHandler, InputCommand, InputSource
from ..core.logger import get_logger

logger = get_logger(__name__)


class ButtonController:
    """
    Handles physical GPIO button input and forwards events
    to the InputHandler as InputCommands.
    """

    def __init__(
        self,
        input_handler: InputHandler,
        *,
        pin_next: int = 24,
        pin_select: int = 23,
        pull_up: bool = True,
        debounce_ms: int = 200
    ):
        """
        Initialize GPIO buttons.

        Args:
            input_handler (InputHandler): Central input handler.
            pin_next (int): BCM pin number for NEXT button.
            pin_select (int): BCM pin number for SELECT button.
            pull_up (bool): Use internal pull-up resistors.
            debounce_ms (int): Debounce time in milliseconds.
        """

        self.input_handler = input_handler
        self.pin_next = pin_next
        self.pin_select = pin_select
        self.debounce_ms = debounce_ms

        GPIO.setmode(GPIO.BCM)

        pud = GPIO.PUD_UP if pull_up else GPIO.PUD_DOWN
        edge = GPIO.FALLING if pull_up else GPIO.RISING

        GPIO.setup(self.pin_next, GPIO.IN, pull_up_down=pud)
        GPIO.setup(self.pin_select, GPIO.IN, pull_up_down=pud)

        GPIO.add_event_detect(
            self.pin_next,
            edge,
            callback=self._on_next_pressed,
            bouncetime=self.debounce_ms
        )

        GPIO.add_event_detect(
            self.pin_select,
            edge,
            callback=self._on_select_pressed,
            bouncetime=self.debounce_ms
        )

        logger.info(
            f"ButtonController initialized: "
            f"NEXT pin={self.pin_next}, "
            f"SELECT pin={self.pin_select}, "
            f"debounce={self.debounce_ms}ms"
        )

    def __enter__(self):
        logger.debug("Entering ButtonController context")
        return self

    def __exit__(self, exc_type, exc, tb):
        logger.info("Exiting ButtonController context")
        self.cleanup()

        # Do not suppress exceptions
        return False

    def _on_next_pressed(self, channel: int):
        logger.debug(f"GPIO NEXT button pressed (pin={channel})")

        self.input_handler.handle(
            command=InputCommand.NEXT,
            source=InputSource.GPIO,
        )

    def _on_select_pressed(self, channel: int):
        logger.debug(f"GPIO SELECT button pressed (pin={channel})")

        self.input_handler.handle(
            command=InputCommand.SELECT,
            source=InputSource.GPIO,
        )

    def cleanup(self):
        """Remove GPIO event detection for managed pins."""
        logger.info("Cleaning up ButtonController GPIO resources")

        GPIO.remove_event_detect(self.pin_next)
        GPIO.remove_event_detect(self.pin_select)