import asyncio
from collections import defaultdict
from enum import Enum, auto
from functools import partial
import json
from typing import Callable


from ..remote.microdot_server import ControllerServer
from .logger import get_logger

logger = get_logger(__name__)

class InputCommand(Enum):
    # Navigation Commands
    NEXT = auto()
    PREVIOUS = auto()
    SELECT = auto()

    # Capture Commands
    START_CAPTURE = auto()
    STOP_CAPTURE = auto()

    # Pan/Tilt Commands
    PAN = auto()
    TILT = auto()

    # System Commands
    SHUTDOWN = auto()
    REBOOT = auto()

    # Remote Commands
    FETCH_SETTINGS = auto()
    UPDATE_SETTINGS = auto()
    LOAD_DEFAULT_SETTINGS = auto()
    FETCH_MEDIA_DIRS = auto()
    FETCH_MEDIA = auto()
    REQUEST_SESSION_INFO = auto()

class InputSource(Enum):
    GPIO = auto()
    WEBSOCKET = auto()
    SYSTEM = auto()

class InputScope(str, Enum):
    DEFAULT = "default"
    MENU = "menu"
    CAPTURE_LOOP = "capture_loop"

class InputHandler:
    """
    Centralized input handling system that manages input commands
    from various sources and dispatches them to registered callbacks.
    """
    def __init__(self):
        """Initialize the InputHandler with empty listener mappings and default scope."""

        self._listeners: dict[str, dict[InputCommand, list[Callable]]] = defaultdict(lambda: defaultdict(list))
        self._scope_change_listeners: list[Callable] = []
        self.active_scope = InputScope.DEFAULT
        logger.info(f"InputHandler initialized with scope '{self.active_scope}'")

    def set_scope(self, scope: InputScope):
        """
        Set the active input scope.
        
          Args:
            scope (InputScope): The scope to set as active.
        """

        if scope == self.active_scope:
            logger.debug(f"Scope already active: '{scope}'")
            return
        
        logger.info(f"Switching input scope from '{self.active_scope}' to '{scope}'")

        self.active_scope = scope

        for callback in self._scope_change_listeners:
            try:
                callback(new_scope=scope)
            except Exception as e:
                logger.exception(
                    f"Error while calling scope change listener {callback.__qualname__} "
                    f" - {e}"
                )

    def clear_scope(self, scope: InputScope):
        """
        Clear all input bindings for a given scope.

        Args:
            scope (InputScope): The scope to clear.
        """

        if scope in self._listeners:
            count = sum(len(cbs) for cbs in self._listeners[scope].values())
            self._listeners[scope].clear()
            logger.info(f"Cleared {count} input bindings from scope '{scope}'")
        else:
            logger.debug(f"Tried to clear non-existent scope '{scope}'")

    def add_scope_change_listener(self, callback: Callable, **kwargs):
        """
        Register a listener to be called when the input scope changes.

        Args:
            callback (Callable): A function to call on scope change.
        """
        callback = partial(callback, **kwargs) if kwargs else callback

        if callback in self._scope_change_listeners:
            logger.debug(f"Duplicate scope change listener ignored: {callback.__qualname__}")
            return

        self._scope_change_listeners.append(callback)
        logger.debug(f"Registered scope change listener: {callback.__qualname__}")

    def register(self, scope: InputScope, command: InputCommand, callback: Callable):
        """
        Register a callback for a specific input command within a given scope.
        
        Args:
            scope (InputScope): The scope for the input command.
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

    def unregister(self, scope: InputScope, command: InputCommand, callback: Callable):
        """
        Unregister a callback for a specific input command within a given scope.

        Args:
            scope (InputScope): The scope for the input command.
            command (InputCommand): The input command to unregister.
            callback (Callable): The function to remove from the handlers list.
        """

        if callback in self._listeners[scope][command]:
            self._listeners[scope][command].remove(callback)
            logger.debug(
                f"Unregistered input: Scope='{scope}', Command={command.name}, "
                f"Handler={callback.__qualname__}"
            )
        else:
            logger.debug(
                f"Tried to unregister non-existent handler: Scope='{scope}', "
                f"Command={command.name} -> {callback.__qualname__}"
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
            f"Scope='{self.active_scope}', "
            f"Source={source.name}"
        )

        callbacks = self._listeners[self.active_scope].get(command, [])
        if not callbacks:
            logger.debug(
                f"No handlers for Command={command.name} "
                f"in Scope='{self.active_scope}' "
                f"(Source={source.name})"
            )
            return

        for callback in callbacks:
            try:
                logger.debug(
                    f"Executing {command.name} -> {callback.__qualname__} "
                    f"(Source={source.name})"
                )
                callback(**kwargs)
            except Exception as e:
                logger.exception(
                    f"Error while handling Command: {command.name} "
                    f"in Scope:'{self.active_scope}' "
                    f"with {callback.__qualname__}"
                    f" (Source={source.name})"
                    f" - {e}"
                )

                raise

class RemoteInput:
    def __init__(self, server: ControllerServer, input_handler: InputHandler):
        self.server = server
        self.input_handler = input_handler

    async def start_listening(self):
        while True:
            if self.server.incoming_messages:
                message = self.server.incoming_messages.pop(0)
                await self.handle_message(message)
            
            await asyncio.sleep(0)      # yield back to scheduler
    
    async def handle_message(self, message):
        try:
            if isinstance(message, str):
                message = json.loads(message)  # Parse JSON string to dict
            
            if message.get("type") == "input_command":
                command_str = message.get("command")
                args = message.get("args", None)
                try:
                    command = InputCommand[command_str]  # Convert string to InputCommand enum
                    if args:
                        self.input_handler.handle(command=command, source=InputSource.WEBSOCKET, args=args)
                    else:
                        self.input_handler.handle(command=command, source=InputSource.WEBSOCKET)
                    logger.debug(f"Handled remote input command: {command}")
                except KeyError:
                    logger.error(f"Invalid remote input command received: {command_str}")
            else:
                logger.error(f"Unknown message type received: {message.get('type')}")
        except Exception as e:
            logger.error(f"Error handling remote message: {e}")