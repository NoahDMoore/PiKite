"""
A simple web server using Microdot to handle WebSocket connections for real-time communication and control.

Usage:
    server = ControllerServer(port=5000)
    server.start()  # Start the web server (must be run within an asyncio event loop)
    server.send({"command": "start"})  # Send a command to the client
    message = server.get()  # Retrieve incoming messages from the client
"""

import asyncio
import bcrypt
import json
import os
import secrets
import time

from dotenv import load_dotenv
from microdot import Request, Microdot, send_file
from microdot.websocket import WebSocket, with_websocket

from ..core.logger import get_logger, register_websocket_handler
from ..system.storage import StorageManager, resolve_safe_path

# Setup Logger
logger = get_logger(__name__)

class ControllerServer:
    """
    A simple web server using Microdot to handle WebSocket connections for real-time communication and control.
    """
    def __init__(self, port: int=5000, remote_logging: bool=True):
        """
        Initialize the web server and set up routing.

        Args:
            port (int): The port number on which the server will listen.
        """
        self.app = Microdot()
        self.port = port

        # Message Buffers
        self.incoming_messages = asyncio.Queue()
        self.outgoing_messages = asyncio.Queue()
        self.websocket_connected = False

        # Initialize Storage Manager
        self.storage = StorageManager()

        # Load password hash from .env
        load_dotenv(self.storage.BASE_DIR / ".env", override=True)

        # Register Remote Logging Handler if enabled
        if remote_logging:
            register_websocket_handler(self) # Register this server as a handler for remote logging messages from the logger module

        # Authentication
        self.active_tokens = {}

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
                token = request.args.get('token')
                
                if not token:
                    logger.warning(f"WebSocket connection attempt without token from client: {request.client_addr}")
                    await ws.send(json.dumps({"error": "No Token Provided. Connection Rejected.", "force_logout": True}))
                    await ws.close()
                    return
                
                if token not in self.active_tokens:
                    logger.warning(f"WebSocket connection attempt with invalid token from client: {request.client_addr}")
                    await ws.send(json.dumps({"error": "Invalid Token. Connection Rejected.", "force_logout": True}))
                    await ws.close()
                    return
                
                if self.active_tokens[token] < time.time():
                    logger.warning(f"WebSocket connection attempt with expired token from client: {request.client_addr}")
                    await ws.send(json.dumps({"error": "Expired Token. Connection Rejected.", "force_logout": True}))
                    await ws.close()
                    return
                
                time_left = int(self.active_tokens[token] - time.time())
                expiration_str = f"{time_left // 60}m {time_left % 60}s" if time_left >= 60 else f"{time_left}s"
                logger.info(f"WebSocket connection established with client: {request.client_addr}. Session token expires in {expiration_str}.")
                self.websocket_connected = True
                try:
                    await self.register_websocket_client(ws) # Register the WebSocket connection
                finally:
                    self.websocket_connected = False
                    self.outgoing_messages = asyncio.Queue() # Clear outgoing messages buffer when client disconnects
                    logger.info(f"WebSocket connection closed for client: {request.client_addr}")
            except Exception as e:
                logger.warning(f"WebSocket connection error for client {request.client_addr}: {e}")

        # MIME types for static files (images, css, js)
        MIME_TYPES = {
            '.png':  'image/png',
            '.jpg':  'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.gif':  'image/gif',
            '.svg':  'image/svg+xml',
            '.css':  'text/css',
            '.js':   'application/javascript',
            '.html': 'text/html'
        }

        # Web Server Routes
        
        @self.app.route('/static/<path:path>')
        async def static(request: Request, path):
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
            try:
                file_path = str(resolve_safe_path(self.storage.WEB_ROOT / "static", path))
            except ValueError as e:
                logger.error(f"Unauthorized Static File Request: {e} from client ({request.client_addr})")
                return

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
            
        @self.app.route('/media/<path:path>')
        async def serve_capture_session_media(request: Request, path: str):
            """
            Serve media files from PiKite's media output directory.
            
            Args:
                request: The incoming request object.
                path (str): The path to the requested media file.
            
            Returns:
                The requested file with the appropriate content type, or an error message if not found.

            Raises:
                FileNotFoundError: If the requested file does not exist.
                OSError: If there is an issue reading the file.
                Exception: For any other unexpected errors.
            """
            request_path = path.strip().removeprefix("/media/")
            try:
                file_path = str(resolve_safe_path(self.storage.MEDIA_OUTPUT_DIR, request_path))
            except ValueError as e:
                logger.error(f"Unauthorized Media Request: {e} from client ({request.client_addr})")
                return

            # Get extension without os.path
            dot = file_path.rfind('.')
            ext = file_path[dot:].lower() if dot != -1 else ''
            content_type = MIME_TYPES.get(ext, 'application/octet-stream')

            try:
                with open(file_path, 'rb') as f:
                    return f.read(), 200, {'Content-Type': content_type}
            except FileNotFoundError:
                logger.error(f"Media File Not Found for client ({request.client_addr}) request: {file_path}")
                return 'Error 404: File not found', 404
            except OSError:
                logger.error(f"OS Error reading media file for client ({request.client_addr}) request: {file_path}")
                return 'Error 500: Could not read file', 500
            except Exception as e:
                logger.error(f"Unknown error serving media file for client ({request.client_addr}) request: {file_path}: {e}")
                return 'Error 500: Internal Server Error', 500

        @self.app.route('/')
        async def root(request: Request):
            """
            Serve the root HTML file (index.html) for the web interface.
            
            Args:
                request: The incoming request object.
            
            Returns:
                The requested file with the appropriate content type, or an error message if not found.
            
            Raises:
                FileNotFoundError: If the index.html file does not exist.
                OSError: If there is an issue reading the file.
                Exception: For any other unexpected errors.
            """
            # Default to index.html
            file_path = self.storage.WEB_ROOT / 'index.html'
            try:
                return send_file(str(file_path))
            except FileNotFoundError:
                logger.error(f"Root File Not Found for client ({request.client_addr}) request.")
                return "Error 404: File not found", 404
            except Exception as e:
                logger.error(f"Unknown error serving root file for client ({request.client_addr}) request: {e}")
                return "Error 500: Internal Server Error", 500

        @self.app.route('/<path:path>')
        async def serve_html(request: Request, path: str):
            """
            Serve only HTML files from the web root directory.
            
            Args:
                request: The incoming request object.
                path (str): The path to the requested HTML file.
            
            Returns:
                The requested HTML file, or an error message if not found or if the path is invalid
            
            Raises:
                FileNotFoundError: If the requested HTML file does not exist.
                OSError: If there is an issue reading the file.
                Exception: For any other unexpected errors.
            """
            if not (path.endswith('.html') and '/' not in path and '\\' not in path):
                return "Error 404: File not found", 404
            file_path = self.storage.WEB_ROOT / path
            try:
                return send_file(str(file_path))
            except FileNotFoundError:
                logger.error(f"HTML File Not Found for client ({request.client_addr}) request: {file_path}")
                return "Error 404: File not found", 404
            except Exception as e:
                logger.error(f"Unknown error serving HTML file for client ({request.client_addr}) request: {e}")
                return "Error 500: Internal Server Error", 500

        # Login Route
        @self.app.route('/login', methods=['POST'])
        async def login(request: Request):
            """
            Handle user login requests.

            Args:
                request: The incoming request object.

            Returns:
                A JSON response indicating the success or failure of the login attempt.
            """
            data = request.json
            username = data.get('username') # type: ignore
            password = data.get('password').encode() # type: ignore

            stored_password_hash = os.environ.get('PIKITE_PASSWORD_HASH').encode() # type: ignore

            # Placeholder for actual authentication logic
            if not username == "pikite_admin" or not bcrypt.checkpw(password, stored_password_hash):
                logger.warning(f"Failed login attempt with username: '{username}' from client: {request.client_addr}")
                return {"error": "Invalid Credentials. Login Failed."}, 401
            
            del(password) # Clear password from memory
            
            # Generate a Secure Token for the Client
            token = self.register_auth_token()
            logger.info(f"User '{username}' logged in successfully. Issued a new session token.")
            return {"token": token}

    async def register_websocket_client(self, ws: WebSocket):
        """
        Register a WebSocket connection and start RX and TX loops.

        Args:
            ws: The WebSocket connection object.
        """
        try:
            await asyncio.gather(self._rx_loop(ws), self._tx_loop(ws))
        except Exception as e:
            logger.info(f"WebSocket Error: {e}")

    def register_auth_token(self) -> str:
        """
        Generate and register a new authentication token for websocket clients.
        
        Returns:
            str: The generated authentication token.
        """
        token = secrets.token_urlsafe(32)
        self.active_tokens[token] = time.time() + 1800  # Token valid for 30 minutes
        return token

    async def _rx_loop(self, ws: WebSocket):
        """
        Receive messages from the WebSocket client and store them in the incoming_messages buffer.

        Args:
            ws: The WebSocket connection object.
        """
        while True:
            message = await ws.receive() # Receive message from websocket client
            await self.incoming_messages.put(message) # Store message for retrieval in the incoming_messages buffer
            logger.debug(f"RX: {message}", extra={"skip_remote": True}) # Log the message received, but don't send via the remote logging handler to avoid infinite loops.

            await asyncio.sleep(0)      # yield back to scheduler

    async def _tx_loop(self, ws: WebSocket):
        """
        Send messages from the outgoing_messages buffer to the WebSocket client.
        
        Args:
            ws: The WebSocket connection object.

        Raises:
            TypeError: If the message type is not string or dict.
        """
        while True:
            message = await self.outgoing_messages.get() # Wait for a message to be available in the outgoing_messages queue
            try:
                # If the raw message is a string, wrap it in JSON object
                if isinstance(message, str):
                    payload = json.dumps({"state": "Message: " + message})
                elif isinstance(message, dict):
                    payload = json.dumps(message)
                elif isinstance(message, bytes):
                    payload = message
                else:
                    raise TypeError

                logger.debug(f"TX: {payload}", extra={"skip_remote": True}) # Log the message being sent, but don't send via the remote logging handler to avoid infinite loops.
                await ws.send(payload)  # Send message to websocket client
            except TypeError:
                logger.error("Invalid Message Type: Messages must be a string or dict")
                
            await asyncio.sleep(0)      # yield back to scheduler

    async def get(self):
        """
        Retrieve the oldest message from the incoming_messages buffer.

        Returns:
            The oldest message from the incoming_messages queue.
        """
        return await self.incoming_messages.get()
    
    def send(self, message: str | dict):
        """
        Add a message to the outgoing_messages buffer to be sent to the WebSocket client.
        Only queue if a websocket client is connected.
        
        Args:
            message (str | dict): The message to send. Can be a string or a dictionary.
        """
        try:
            if self.websocket_connected:
                self.outgoing_messages.put_nowait(message) # Add message to the outgoing_messages queue to be sent to the client
        except asyncio.QueueFull as e:
            logger.error(f"Outgoing message queue is full. Message not sent: {message}. Error: {e}")
        except Exception as e:
            logger.error(f"Unexpected error while sending message: {message}. Error: {e}")
    
    def start(self):
        """
        Start the web server on the specified port.
        
        Returns:
            An asyncio Task that runs the web server.
        """
        return asyncio.create_task(self.app.start_server(port=self.port))