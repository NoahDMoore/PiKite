from pikite.core.input_handler import InputCommand, InputHandler, InputSource
from pikite.remote.remote_server import RemoteServer
from pikite.utils.logger import get_logger

import asyncio
import json

# Configure Logger
logger = get_logger(__name__)


class RemoteInputListener:
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