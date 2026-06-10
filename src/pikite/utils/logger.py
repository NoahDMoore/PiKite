import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

# Configure Minimal Logger on Import
logger = logging.getLogger("PiKite")    # Create a logger for the given name
logger.addHandler(logging.StreamHandler())

# Specify Log Format
LOG_FORMAT = logging.Formatter(
    fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)

def configure_logger(
        log_level: str = "INFO",
        use_console_handler: bool = True,
        use_file_handler: bool = False,
        log_file: Path | None = None
    ):
    set_log_level(log_level)

    # Setup Handlers
    unset_console_handler() # Remove existing handlers
    unset_file_handler()

    if use_console_handler:
        register_console_handler()

    if use_file_handler:
        if log_file is None:
            logger.error("Cannot register a file handler for the logger. No log file provided.")
            return
        register_file_handler(log_file)

def register_console_handler():
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(LOG_FORMAT)
    logger.addHandler(console_handler)

def register_file_handler(log_file: Path):
    file_handler = TimedRotatingFileHandler(
        filename = log_file,    # Base log file location/file_name
        when = 'midnight',      # Create a new log file at midnight
        interval = 1,           # Create the new log file every night
        backupCount = 30        # Store 30 days of logs
    )
    file_handler.setFormatter(LOG_FORMAT)
    logger.addHandler(file_handler)

def unset_console_handler() -> None:
    """
    Remove the stream handler from the logger to disable console output.
    """
    for handler in list(logger.handlers):
        if type(handler) is logging.StreamHandler:
            logger.removeHandler(handler)
            handler.close()

    logger.debug("Console handler removed from logger.")

def unset_file_handler() -> None:
    """
    Remove the file handler from the logger to disable file output.
    """
    for handler in list(logger.handlers):
        if isinstance(handler, logging.FileHandler):
            logger.removeHandler(handler)
            handler.close()
            
    logger.debug("File handler removed from logger.")

def get_logger(name: str) -> logging.Logger:
    """
    Return a logger with a standard format and file handler.
    Args:
        name (str): Name of the logger, typically __name__ of the module.
        
    Returns:
        logging.Logger: A descendant logger of the root 'PiKite' logger instance.
    """
    
    child_logger = logger.getChild(name)
    logger.debug(f"Registered PiKite Child Logger: {child_logger.name}")
    return child_logger

def set_log_level(level_name: str) -> None:
    """
    Update logging level at runtime.
    
    Args:
        level_name (str): Logging level as a string (e.g., "DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL").

    Raises:
        ValueError: If the provided level_name is not a valid logging level.
    """
    level = getattr(logging, level_name.upper(), None)
    if level is None:
        try:
            raise ValueError(f"Invalid log level: {level_name}")
        except ValueError as e:
            logger.error(f"Error: {e} - Defaulting to INFO level.")
            level = logging.INFO
            
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)

    logger.info(f"Log level set to {level_name}")

def register_websocket_handler(server) -> None:
    """
    Register a WebSocket handler to send log messages to connected clients.

    Args:
        server: The WebSocket server instance to which the handler will send log messages.
    """
    if any(isinstance(h, WebSocketHandler) for h in logger.handlers):
        return

    websocket_handler = WebSocketHandler(server)
    websocket_handler.setFormatter(logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(websocket_handler)
    logger.debug("WebSocket handler registered to logger.")

class WebSocketHandler(logging.Handler):
    """
    Custom logging handler that sends log messages to connected WebSocket clients.
    """
    def __init__(self, server):
        super().__init__()
        self.server = server

    def filter(self, record):
        return not getattr(record, "skip_remote", False)

    def emit(self, record):
        try:
            if not self.server.websocket_connected:
                raise ConnectionError("WebSocket connection is not established.")

            msg = self.format(record)

            # Push into your existing TX pipeline
            self.server.send({
                "type": "log",
                "level": record.levelname,
                "logger": record.name,
                "message": record.getMessage(),
                "timestamp": record.created
            })

        except ConnectionError as e:
            pass
            #logger.debug(f"WebSocketHandler: {e} - Log message not sent to remote clients.", extra={"skip_remote": True})
        except Exception:
            self.handleError(record)