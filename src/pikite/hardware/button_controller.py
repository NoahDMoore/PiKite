import RPi.GPIO as GPIO
from typing import Optional

from ..core.input_handler import InputHandler, InputCommand, InputSource
from ..core.logger import get_logger

logger = get_logger(__name__)


class ButtonController:
    """
    Handles physical GPIO button input and forwards events
    to the InputHandler as InputCommands.
    
    Supports dynamic command assignment and scope-aware button mappings.
    Button commands are automatically remembered and restored when entering/exiting scopes.
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
        
        # Scope-aware command mappings: scope -> (next_command, select_command)
        self._scope_commands: dict[str, tuple[InputCommand, InputCommand]] = {}
        # Store initial commands for default scope
        self._scope_commands[input_handler._active_scope] = (next_command, select_command)

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

    def cleanup(self):
        """Remove GPIO event detection for managed pins."""
        logger.info("Cleaning up ButtonController GPIO resources")

        GPIO.remove_event_detect(self.pin_next)
        GPIO.remove_event_detect(self.pin_select)

    def set_commands(self, *, next_command: Optional[InputCommand] = None, select_command: Optional[InputCommand] = None, scope: Optional[str] = None):
        """
        Dynamically update the commands emitted by button presses.
        
        Updates are stored per-scope and automatically recalled when entering/exiting scopes.
        
        Args:
            next_command (InputCommand, optional): New command for NEXT button. If None, unchanged.
            select_command (InputCommand, optional): New command for SELECT button. If None, unchanged.
            scope (str, optional): Scope to update. If None, uses current active scope.
        """
        target_scope = scope or self.input_handler._active_scope
        
        # Get existing commands for this scope, or use current if not yet set
        existing_next, existing_select = self._scope_commands.get(
            target_scope,
            (self.next_command, self.select_command)
        )
        
        # Update with new values
        new_next = next_command if next_command is not None else existing_next
        new_select = select_command if select_command is not None else existing_select
        
        # Store in scope mapping
        self._scope_commands[target_scope] = (new_next, new_select)
        
        # If updating current scope, apply immediately
        if target_scope == self.input_handler._active_scope:
            self.next_command = new_next
            self.select_command = new_select
            
            if next_command is not None:
                logger.info(f"Updated NEXT button command to {next_command} in scope '{target_scope}'")
            if select_command is not None:
                logger.info(f"Updated SELECT button command to {select_command} in scope '{target_scope}'")
        else:
            logger.info(f"Stored button commands for scope '{target_scope}' (not yet active)")

    def sync_scope(self, new_scope: str):
        """
        Synchronize button commands with a scope change in the InputHandler.
        
        This method should be called when the InputHandler's active scope changes
        to restore the button mappings for that scope.
        
        Args:
            new_scope (str): The new active scope from InputHandler.
        """
        if new_scope in self._scope_commands:
            self.next_command, self.select_command = self._scope_commands[new_scope]
            logger.info(f"Restored button commands for scope '{new_scope}': NEXT={self.next_command.name}, SELECT={self.select_command.name}")
        else:
            # If scope not yet configured, use current commands as default for this scope
            self._scope_commands[new_scope] = (self.next_command, self.select_command)
            logger.info(f"Initialized scope '{new_scope}' with current button commands")