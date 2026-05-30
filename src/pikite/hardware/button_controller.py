import RPi.GPIO as GPIO
from typing import Optional

from ..core.constants import PiKiteMode
from ..core.input_handler import InputHandler, InputCommand, InputSource
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ButtonController:
    """
    Handles physical GPIO button input and forwards events
    to the InputHandler as InputCommands.
    
    Supports dynamic command assignment and mode-aware button mappings.
    Button commands are automatically remembered and restored when entering/exiting modes.
    """

    def __init__(
        self,
        input_handler: InputHandler,
        *,
        pin_next: int = 23,
        pin_select: int = 24,
        pull_up: bool = True,
        debounce_ms: int = 200,
        next_command: InputCommand = InputCommand.NEXT,
        select_command: InputCommand = InputCommand.SELECT
    ):
        """
        Initialize GPIO buttons.

        Args:
            input_handler (InputHandler): Central input handler.
            pin_next (int): BCM pin number for NEXT button.
            pin_select (int): BCM pin number for SELECT button.
            pull_up (bool): Use internal pull-up resistors.
            debounce_ms (int): Debounce time in milliseconds.
            next_command (InputCommand): Command to emit on NEXT button press. Default: NEXT.
            select_command (InputCommand): Command to emit on SELECT button press. Default: SELECT.
        """

        self.input_handler = input_handler
        self.pin_next = pin_next
        self.pin_select = pin_select
        self.debounce_ms = debounce_ms
        self.next_command = next_command
        self.select_command = select_command
        
        # mode-aware command mappings: mode -> (next_command, select_command)
        self._mode_commands: dict[PiKiteMode, tuple[InputCommand, InputCommand]] = {}
        # Store initial commands for default mode
        self._mode_commands[input_handler.active_mode] = (next_command, select_command)

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
        self.close()

        # Do not suppress exceptions
        return False

    def _on_next_pressed(self, channel: int):
        logger.debug(f"GPIO NEXT button pressed (pin={channel}), emitting {self.next_command}")

        self.input_handler.handle(
            command=self.next_command,
            source=InputSource.GPIO,
        )

    def _on_select_pressed(self, channel: int):
        logger.debug(f"GPIO SELECT button pressed (pin={channel}), emitting {self.select_command}")

        self.input_handler.handle(
            command=self.select_command,
            source=InputSource.GPIO,
        )

    def close(self):
        """Remove GPIO event detection for managed pins."""
        logger.info("Cleaning up ButtonController GPIO resources")

        GPIO.remove_event_detect(self.pin_next)
        GPIO.remove_event_detect(self.pin_select)
        GPIO.cleanup([self.pin_next, self.pin_select])

    def set_commands(self, *, next_command: Optional[InputCommand] = None, select_command: Optional[InputCommand] = None, mode: Optional[PiKiteMode] = None):
        """
        Dynamically update the commands emitted by button presses.
        
        Updates are stored per-mode and automatically recalled when entering/exiting modes.
        
        Args:
            next_command (InputCommand, optional): New command for NEXT button. If None, unchanged.
            select_command (InputCommand, optional): New command for SELECT button. If None, unchanged.
            mode (PiKiteMode, optional): mode to update. If None, uses current active mode.
        """
        target_mode = mode or self.input_handler.active_mode
        
        # Get existing commands for this mode, or use current if not yet set
        existing_next, existing_select = self._mode_commands.get(
            target_mode,
            (self.next_command, self.select_command)
        )
        
        # Update with new values
        new_next = next_command if next_command is not None else existing_next
        new_select = select_command if select_command is not None else existing_select
        
        # Store in mode mapping
        self._mode_commands[target_mode] = (new_next, new_select)
        
        # If updating current mode, apply immediately
        if target_mode == self.input_handler.active_mode:
            self.next_command = new_next
            self.select_command = new_select
            
            if next_command is not None:
                logger.info(f"Updated NEXT button command to {next_command} in mode '{target_mode}'")
            if select_command is not None:
                logger.info(f"Updated SELECT button command to {select_command} in mode '{target_mode}'")
        else:
            logger.info(f"Stored button commands for mode '{target_mode}' (not yet active)")

    def sync_mode(self, new_mode: PiKiteMode, **kwargs):
        """
        Synchronize button commands with a mode change in the InputHandler.
        
        This method should be called when the InputHandler's active mode changes
        to restore the button mappings for that mode.
        
        Args:
            new_mode (PiKiteMode): The new active mode from InputHandler.
        """
        if new_mode in self._mode_commands:
            self.next_command, self.select_command = self._mode_commands[new_mode]
            logger.info(f"Restored button commands for mode '{new_mode}': NEXT={self.next_command.name}, SELECT={self.select_command.name}")
        else:
            # If mode not yet configured, use current commands as default for this mode
            self._mode_commands[new_mode] = (self.next_command, self.select_command)
            logger.info(f"Initialized mode '{new_mode}' with current button commands")