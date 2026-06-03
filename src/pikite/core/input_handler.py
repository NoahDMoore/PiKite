import asyncio
from collections import defaultdict
from enum import Enum, auto
from functools import partial
import json
from typing import Callable

from .modes.pikite_mode import PiKiteMode
from ..remote.remote_server import RemoteServer
from ..utils.logger import get_logger

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

    # Set Baseline Altitude
    SET_BASELINE_ALTITUDE = auto()

    # System Commands
    DISPLAY_SYSTEM_INFO = auto()
    SHUTDOWN = auto()
    REBOOT = auto()
    EXIT = auto()

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

class InputHandler:
    """
    Centralized input handling system that manages input commands
    from various sources and dispatches them to registered callbacks.
    """
    def __init__(self):
        """Initialize the InputHandler with empty listener mappings and default mode."""

        self._listeners: dict[str, dict[InputCommand, list[Callable]]] = defaultdict(lambda: defaultdict(list))
        self._mode_change_listeners: list[Callable] = []
        self.active_mode = PiKiteMode.DEFAULT
        logger.info(f"InputHandler initialized with mode '{self.active_mode}'")

    def set_mode(self, mode: PiKiteMode):
        """
        Set the active input mode.
        
          Args:
            mode (PiKiteMode): The mode to set as active.
        """

        if mode == self.active_mode:
            logger.debug(f"mode already active: '{mode}'")
            return
        
        logger.info(f"Switching input mode from '{self.active_mode}' to '{mode}'")

        self.active_mode = mode

        for callback in self._mode_change_listeners:
            try:
                callback(new_mode=mode)
            except Exception as e:
                logger.exception(
                    f"Error while calling mode change listener {callback.__qualname__} "
                    f" - {e}"
                )

    def clear_mode(self, mode: PiKiteMode):
        """
        Clear all input bindings for a given mode.

        Args:
            mode (PiKiteMode): The mode to clear.
        """

        if mode in self._listeners:
            count = sum(len(cbs) for cbs in self._listeners[mode].values())
            self._listeners[mode].clear()
            logger.info(f"Cleared {count} input bindings from mode '{mode}'")
        else:
            logger.debug(f"Tried to clear non-existent mode '{mode}'")

    def add_mode_change_listener(self, callback: Callable, **kwargs):
        """
        Register a listener to be called when the input mode changes.

        Args:
            callback (Callable): A function to call on mode change.
        """
        callback = partial(callback, **kwargs) if kwargs else callback

        if callback in self._mode_change_listeners:
            logger.debug(f"Duplicate mode change listener ignored: {callback.__qualname__}")
            return

        self._mode_change_listeners.append(callback)
        logger.debug(f"Registered mode change listener: {callback.__qualname__}")

    def register(self, mode: PiKiteMode, command: InputCommand, callback: Callable):
        """
        Register a callback for a specific input command within a given mode.
        
        Args:
            mode (PiKiteMode): The mode for the input command.
            command (InputCommand): The input command to register.
            callback (Callable): The function to call when the command is received.
        """

        if callback in self._listeners[mode][command]:
            logger.debug(
                f"Duplicate input registration ignored: mode={mode}: Command={command} -> {callback.__qualname__}"
            )
            return

        self._listeners[mode][command].append(callback)

        logger.debug(
            f"Registered input: mode='{mode}', Command={command.name}, "
            f"Handler={callback.__qualname__}"
        )

    def unregister(self, mode: PiKiteMode, command: InputCommand, callback: Callable):
        """
        Unregister a callback for a specific input command within a given mode.

        Args:
            mode (PiKiteMode): The mode for the input command.
            command (InputCommand): The input command to unregister.
            callback (Callable): The function to remove from the handlers list.
        """

        if callback in self._listeners[mode][command]:
            self._listeners[mode][command].remove(callback)
            logger.debug(
                f"Unregistered input: mode='{mode}', Command={command.name}, "
                f"Handler={callback.__qualname__}"
            )
        else:
            logger.debug(
                f"Tried to unregister non-existent handler: mode='{mode}', "
                f"Command={command.name} -> {callback.__qualname__}"
            )

    def handle(self, *, command: InputCommand, source: InputSource, **kwargs):
        """
        Handle an input command by invoking all registered callbacks for the current mode.

        Args:
            command (InputCommand): The input command to handle.
            source (InputSource): The source of the input.
            **kwargs: Additional keyword arguments to pass to the callbacks.
        """        
        logger.debug(
            f"Input received: Command={command.name}, "
            f"mode='{self.active_mode}', "
            f"Source={source.name}"
        )

        callbacks = self._listeners[self.active_mode].get(command, [])
        if not callbacks:
            logger.debug(
                f"No handlers for Command={command.name} "
                f"in mode='{self.active_mode}' "
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
                    f"in mode:'{self.active_mode}' "
                    f"with {callback.__qualname__}"
                    f" (Source={source.name})"
                    f" - {e}"
                )

                raise

class RemoteInput:
    def __init__(self, server: RemoteServer, input_handler: InputHandler):
        self.server = server
        self.input_handler = input_handler
        self._active = True

    async def start_listening(self):
        while self._active:
            message = await self.server.get()

            if message == "CLOSE":
                break

            await self.handle_message(message)
            
            await asyncio.sleep(0)      # yield back to scheduler

        logger.info("RemoteInput listener stopped.")
    
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

    def close(self):
        self._active = False

        # Prevent waiting on an empty message queue before stopping
        self.server.incoming_messages.put_nowait("CLOSE")