"""
A simple web server using Microdot to handle WebSocket connections for real-time communication and control.

Usage:
    server = ControllerServer(port=5000)
    server.start()  # Start the web server (must be run within an asyncio event loop)
    server.send({"command": "start"})  # Send a command to the client
    message = server.get()  # Retrieve incoming messages from the client
"""

import json
import asyncio
from microdot import Request, Microdot, send_file
from microdot.websocket import WebSocket, with_websocket
from utils.logger import get_logger

# Setup Logger
logger = get_logger(__name__)

class ControllerServer:
    """
    A simple web server using Microdot to handle WebSocket connections for real-time communication and control.
    """
    def __init__(self, port: int=5000):
        """
        Initialize the web server and set up routing.

        Args:
            port (int): The port number on which the server will listen.
        """
        self.app = Microdot()
        self.port = port

        # Message Buffers
        self.incoming_messages = []
        self.outgoing_messages = []

        # Web Server Routes
        @self.app.route('/')
        async def index(request: Request):
            try:
                return send_file('index.html')
            except FileNotFoundError:
                logger.error(f"Index File Not Found for client ({request.client_addr}) request.")
                return "Error 404: Index file not found", 404
            except Exception as e:
                logger.error(f"Unknown error serving index file for client ({request.client_addr}) request: {e}")
                return "Error 500: Internal Server Error", 500
            
        # Serve static files (images, css, js)
        MIME_TYPES = {
            '.png':  'image/png',
            '.jpg':  'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif':  'image/gif',
            '.css':  'text/css',
            '.js':   'application/javascript',
            '.html': 'text/html'
        }

        @self.app.route('/static/<path:path>')
        def media(request: Request, path):
            """
            Serve static files from the 'static' directory.
            Args:
                request: The incoming request object.
                path (str): The path to the requested static file.
            
            Returns:
                The requested file with the appropriate content type, or an error message if not found.

            Raises:
                FileNotFoundError: If the requested file does not exist.
                OSError: If there is an issue reading the file.
                Exception: For any other unexpected errors.
            """
            file_path = 'static/' + path

            # Get extension without os.path
            dot = file_path.rfind('.')
            ext = file_path[dot:].lower() if dot != -1 else ''
            content_type = MIME_TYPES.get(ext, 'application/octet-stream')

            try:
                with open(file_path, 'rb') as f:
                    return f.read(), 200, {'Content-Type': content_type}
            except FileNotFoundError:
                logger.error(f"Static File Not Found for client ({request.client_addr}) request: {file_path}")
                return 'Error 404: File not found', 404
            except OSError:
                logger.error(f"OS Error reading static file for client ({request.client_addr}) request: {file_path}")
                return 'Error 500: Could not read file', 500
            except Exception as e:
                logger.error(f"Unknown error serving static file for client ({request.client_addr}) request: {file_path}: {e}")
                return 'Error 500: Internal Server Error', 500

        # WebSocket Route
        @self.app.route('/ws')
        @with_websocket
        async def ws(request: Request, ws: WebSocket):
            """
            Handle WebSocket connections for real-time communication.

            Args:
                request: The incoming request object.
                ws: The WebSocket connection object.

            Raises:
                Exception: If there is an error during WebSocket connection or communication.
            """
            try:
                logger.info(f"WebSocket connection established with client: {request.client_addr}")
                await self.register(ws) # Register the WebSocket connection
            except Exception as e:
                logger.warning(f"WebSocket connection error for client {request.client_addr}: {e}")

    async def register(self, ws: WebSocket):
        """
        Register a WebSocket connection and start RX and TX loops.

        Args:
            ws: The WebSocket connection object.
        """
        try:
            await asyncio.gather(self._rx_loop(ws), self._tx_loop(ws))
        except Exception as e:
            logger.info(f"WebSocket connection closed: {e}")

    async def _rx_loop(self, ws: WebSocket):
        """
        Receive messages from the WebSocket client and store them in the incoming_messages buffer.

        Args:
            ws: The WebSocket connection object.
        """
        while True:
            message = await ws.receive()                    # Receive message from websocket client
            self.incoming_messages.append(message)          # Store message for retrieval in the incoming_messages buffer
            logger.debug(f"RX: {message}")

    async def _tx_loop(self, ws: WebSocket):
        """
        Send messages from the outgoing_messages buffer to the WebSocket client.
        
        Args:
            ws: The WebSocket connection object.

        Raises:
            TypeError: If the message type is not string or dict.
        """
        while True:
            try:
                if self.outgoing_messages:
                    raw = self.outgoing_messages.pop(0) # Get the oldest message from the outgoing_messages buffer

                    # If the raw message is a string, wrap it in JSON object
                    if isinstance(raw, str):
                        payload = json.dumps({"state": "Message: " + raw})
                    elif isinstance(raw, dict):
                        payload = json.dumps(raw)
                    else:
                        raise TypeError

                    logger.debug(f"TX: {payload}")
                    await ws.send(payload)  # Send message to websocket client
            except TypeError:
                logger.error("Invalid Message Type: Messages must be a string or dict")
                
            await asyncio.sleep(0)      # yield back to scheduler

    def start(self):
        """
        Start the web server on the specified port.
        
        Returns:
            An asyncio Task that runs the web server.
        """
        return asyncio.create_task(self.app.start_server(port=self.port))
    
    def send(self, message: str | dict):
        """
        Add a message to the outgoing_messages buffer to be sent to the WebSocket client.
        
        Args:
            message (str | dict): The message to send. Can be a string or a dictionary.
        """
        self.outgoing_messages.append(message)

    def get(self):
        """
        Retrieve the oldest message from the incoming_messages buffer.

        Returns:
            The oldest message from the incoming_messages buffer, or None if the buffer is empty.
        """
        return self.incoming_messages.pop(0) if self.incoming_messages else None