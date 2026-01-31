"""
Handles storage paths for logs, media, data, and configuration files.

This module provides a StorageManager class that manages directories for logs,
media (photos and videos), data, and configuration files. All project output
is stored in a single folder within the user's home directory by default.

Typical usage example:
    # Initialize the storage manager
    storage = StorageManager()

    # Get the log file path
    log_file = storage.log_path

    # Generate a new photo path with timestamp
    photo_file = storage.media_path("photos", filename="kite", ext=".jpg")

    # Save a data log
    data_file = storage.data / "altitude_log.csv"
"""

from pathlib import Path
from datetime import datetime

from ..core.constants import CAPTURE_MODES, MEDIA_EXTENSIONS

class StorageManager:
    """
    A class to manage all storage paths for project outputs including logs,
    photos, videos, data, and configuration.

    Attributes:
        BASE_DIR (Path): Base directory of the PiKite project library.
        DEFAULT_CONFIG_FILE (Path): Path to the default configuration file.
        FONTS_DIR (Path): Directory for font files.
        MEDIA_DIR (Path): Directory for static media files.
        MENU_DIR (Path): Directory for menu XML files.
        MENU_FILE (Path): Path to the main menu XML file.
        USER_HOME (Path): Root directory for user-specific output files.
        LOG_FILE (Path): Path to the main log file.
        CONFIG_FILE (Path): Path to the configuration file.
        LOG_DIR (Path): Directory for log files.
        DATA_DIR (Path): Directory for data files.
        CONFIG_DIR (Path): Directory for configuration files.
        USER_MEDIA_DIR (Path): Root directory for user media files.
        PHOTO_OUTPUT_DIR (Path): Directory for storing photos.
        VIDEO_OUTPUT_DIR (Path): Directory for storing videos.
    """

    def __init__(self, root: str | None = None):
        """
        Initialize the StorageManager.

        Args:
            root (str | None): Optional custom root directory. If not provided,
                               defaults to ~/pikite_output.
        """
        # PiKite Library Directories
        self.BASE_DIR = Path(__file__).resolve().parent.parent
        self.DEFAULT_CONFIG_FILE  = self.BASE_DIR / "config" / "default_settings.ini"
        self.FONTS_DIR = self.BASE_DIR / "static" / "fonts"
        self.MEDIA_DIR = self.BASE_DIR / "static" / "media"
        self.MENU_DIR = self.BASE_DIR / "static" / "menus"
        self.MENU_FILE = self.MENU_DIR / "lcd_menu.xml"

        # Set User Root Directory
        self.USER_ROOT = Path(root or Path.home() / "pikite_output")

        # Define User Directories
        self.LOG_DIR = self.USER_ROOT / "logs"
        self.DATA_DIR = self.USER_ROOT / "data"
        self.CONFIG_DIR = self.USER_ROOT / "config"
        self.USER_MEDIA_DIR = self.USER_ROOT / "media"
        self.PHOTO_OUTPUT_DIR = self.USER_MEDIA_DIR / "photos"
        self.VIDEO_OUTPUT_DIR = self.USER_MEDIA_DIR / "videos"

        self._initialize_dirs()

    def _initialize_dirs(self) -> None:
        """Ensure that all required user directories exist. If not, create them."""
        for path in (self.LOG_DIR,
            self.DATA_DIR,
            self.CONFIG_DIR,
            self.PHOTO_OUTPUT_DIR,
            self.VIDEO_OUTPUT_DIR
        ):
            path.mkdir(parents=True, exist_ok=True)

    @property
    def LOG_FILE(self) -> Path:
        """Return the path to the user's log file."""
        return self.LOG_DIR / "pikite.log"
    
    @property
    def CONFIG_FILE(self) -> Path:
        """Return the path to the user's configuration file."""
        return self.CONFIG_DIR / "pikite_settings.ini"
    
    def get_data_file_path(
        self,
        base_name: str="altitude_log",
        use_timestamp: bool=True
    ) -> Path:
        """
        Return the path to the user's data log file.
        
        Args:
            base_name (str): Base name of the data file (default: 'altitude_log')"
            use_timestamp (bool): Whether to append a timestamp to the filename (default: True)

        Returns:
            Path: Full path to the data log file.
        """
        filename = self.get_filename(base_name, ".csv", use_timestamp)
        return self.DATA_DIR / filename

    def new_session_dir(self, mode: CAPTURE_MODES) -> Path | None:
        """
        Create and return a new directory for a capture session based on the current date and time.

        The directory is created under the root media directory with the format:
        YYYY-MM-DD_HH-MM-SS

        Args:
            mode (CAPTURE_MODES): Type of Media (i.e., photo or video):
                                  CAPTURE_MODES.STILL or CAPTURE_MODES.VIDEO

        Returns:
            Path: Path to the newly created session directory, or None if mode is invalid.
        """
        if mode not in (CAPTURE_MODES.STILL, CAPTURE_MODES.VIDEO):
            return None
            
        output_dir = self.PHOTO_OUTPUT_DIR if mode == CAPTURE_MODES.STILL else self.VIDEO_OUTPUT_DIR
        session_dir = output_dir / get_timestamp()
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def media_file_path(
        self,
        mode: CAPTURE_MODES,
        extension: MEDIA_EXTENSIONS,
        base_name: str = "capture",
        use_timestamp: bool = True,
        session_dir: Path | None = None
    ) -> Path:
        """
        Generate a file path for saving media files (photos or videos).

        Args:
            mode (CAPTURE_MODES): Type of Media (i.e., photo or video):
                                  CAPTURE_MODES.STILL or CAPTURE_MODES.VIDEO
            base_name (str): Base name of the file (default: "capture")
            timestamp (bool): Whether to append a timestamp (default: True)
            ext (str): File extension (default: ".jpg")

        Returns:
            Path: Full path to the requested media file.

        Raises:
            ValueError: If mode is not CAPTURE_MODES.STILL or CAPTURE_MODES.VIDEO
        """

        current_session_dir = session_dir or self.new_session_dir(mode) or self.PHOTO_OUTPUT_DIR
        filename = self.get_filename(base_name, extension, use_timestamp)

        if mode == CAPTURE_MODES.STILL:
            return current_session_dir / filename
        elif mode == CAPTURE_MODES.VIDEO:
            return current_session_dir / filename
        else:
            raise ValueError("Mode must be CAPTURE_MODES.STILL or CAPTURE_MODES.VIDEO")
            
    def get_filename(
            self,
            base_name: str,
            extension: str,
            use_timestamp: bool = True
        ) -> str:
        """
        Generate a filename with an optional timestamp.

        Args:
            base (str): Base name of the file.
            ext (str): File extension (including the dot, e.g., ".jpg").
            timestamp (bool): Whether to append a timestamp (default: True).

        Returns:
            str: Generated filename.
        """
        if use_timestamp:
            timestamp = get_timestamp()    # Date format: 2023-10-31_14-30-00
            return f"{base_name}_{timestamp}{extension}"
        return f"{base_name}{extension}"
    
def get_timestamp() -> str:
    """Return the current date and time as a formatted string."""
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")