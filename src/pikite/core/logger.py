import logging
from system.storage import StorageManager

storage = StorageManager()
LOG_FILE = storage.LOG_FILE

logger = logging.getLogger("PiKite")    # Create a logger for the given name

# Set handlers if logger has not already been configured
if not logger.handlers:
    logger.setLevel(logging.INFO)   # Default log level

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # File Handler
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

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
    if not level:
        try:
            raise ValueError(f"Invalid log level: {level_name}")
        except ValueError as e:
            logger.error(f"Error: {e} - Defaulting to INFO level.")
            level = logging.INFO
            
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)

def unset_stream_handler() -> None:
    """
    Remove the stream handler from the logger to disable console output.
    """
    console_handler = next((handler for handler in logger.handlers if isinstance(handler, logging.StreamHandler)), None)
    if console_handler:
        logger.removeHandler(console_handler)
        logger.debug("Stream handler removed from logger.")
    else:
        logger.debug("No stream handler found to remove.")

def unset_file_handler() -> None:
    """
    Remove the file handler from the logger to disable file output.
    """
    file_handler = next((handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)), None)
    if file_handler:
        logger.removeHandler(file_handler)
        logger.debug("File handler removed from logger.")
    else:
        logger.debug("No file handler found to remove.")