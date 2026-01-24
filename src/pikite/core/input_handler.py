from enum import Enum, auto
from collections import defaultdict
from typing import Callable
from .logger import get_logger

logger = get_logger(__name__)

class InputCommand(Enum):
    NEXT = auto()
    PREVIOUS = auto()
    SELECT = auto()
    BACK = auto()
    START_CAPTURE = auto()
    STOP_CAPTURE = auto()
    SHUTDOWN = auto()
    REBOOT = auto()

class InputSource(Enum):
    GPIO = auto()
    WEBSOCKET = auto()
    SYSTEM = auto() 

class InputHandler:
    """
    Centralized input handling system that manages input commands
    from various sources and dispatches them to registered callbacks.
    """
    def __init__(self):
        """Initialize the InputHandler with empty listener mappings and default scope."""

        self._listeners: dict[str, dict[InputCommand, list[Callable]]] = defaultdict(lambda: defaultdict(list))
        self._active_scope = "default"
        logger.info(f"InputHandler initialized with scope '{self._active_scope}'")

    def set_scope(self, scope: str):
        """
        Set the active input scope.
        
          Args:
            scope (str): The scope to set as active.
        """

        if scope == self._active_scope:
            logger.debug(f"Scope already active: '{scope}'")
            return
        
        logger.info(f"Switching input scope from '{self._active_scope}' to '{scope}'")

        self._active_scope = scope

    def clear_scope(self, scope: str):
        """
        Clear all input bindings for a given scope.

        Args:
            scope (str): The scope to clear.
        """

        if scope in self._listeners:
            count = sum(len(cbs) for cbs in self._listeners[scope].values())
            self._listeners[scope].clear()
            logger.info(f"Cleared {count} input bindings from scope '{scope}'")
        else:
            logger.debug(f"Tried to clear non-existent scope '{scope}'")

    def register(self, scope: str, command: InputCommand, callback: Callable):
        """
        Register a callback for a specific input command within a given scope.
        
        Args:
            scope (str): The scope for the input command.
            command (InputCommand): The input command to register.
            callback (Callable): The function to call when the command is received.
        """

        if callback in self._listeners[scope][command]:
            logger.debug(
                f"Duplicate input registration ignored: Scope={scope}: Command={command} -> {callback.__qualname__}"
            )
            return

        self._listeners[scope][command].append(callback)

        logger.debug(
            f"Registered input: Scope='{scope}', Command={command.name}, "
            f"Handler={callback.__qualname__}"
        )


    def handle(self, *, command: InputCommand, source: InputSource, **kwargs):
        """
        Handle an input command by invoking all registered callbacks for the current scope.

        Args:
            command (InputCommand): The input command to handle.
            source (InputSource): The source of the input.
            **kwargs: Additional keyword arguments to pass to the callbacks.
        """        
        logger.info(
            f"Input received: Command={command.name}, "
            f"Scope='{self._active_scope}', "
            f"Source={source.name}"
        )

        callbacks = self._listeners[self._active_scope].get(command, [])

        if not callbacks:
            logger.debug(
                f"No handlers for Command={command.name} "
                f"in Scope='{self._active_scope}' "
                f"(Source={source.name})"
            )
            return

        for callback in callbacks:
            try:
                logger.debug(
                    f"Executing {command.name} -> {callback.__qualname__} "
                    f"(Source={source.name})"
                )
                callback(source=source, **kwargs)
            except Exception:
                logger.exception(
                    f"Error while handling Command: {command.name} "
                    f"in Scope:'{self._active_scope}' "
                    f"with {callback.__qualname__}"
                    f" (Source={source.name})"
                )
