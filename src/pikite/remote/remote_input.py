import asyncio
import json

from .microdot_server import ControllerServer
from ..core.logger import get_logger
from ..core.input_handler import InputCommand, InputSource, InputHandler

# Setup Logger
logger = get_logger(__name__)

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
                try:
                    command = InputCommand[command_str]  # Convert string to InputCommand enum
                    self.input_handler.handle(command=command, source=InputSource.WEBSOCKET)
                    logger.debug(f"Handled remote input command: {command}")
                except KeyError:
                    logger.error(f"Invalid remote input command received: {command_str}")
            else:
                logger.error(f"Unknown message type received: {message.get('type')}")
        except Exception as e:
            logger.error(f"Error handling remote message: {e}")