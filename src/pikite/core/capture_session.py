import csv
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pikite.core.constants as CONSTANTS
from pikite.core.settings import Settings
from pikite.hardware.servos.pan_servo import PanServo
from pikite.hardware.servos.pan_tilt_pattern import PanTiltPattern
from pikite.hardware.servos.tilt_servo import TiltServo
from pikite.system.storage import StorageManager
from pikite.utils.logger import get_logger
from pikite.utils.timer import Timer

# Setup Logger
logger = get_logger(__name__)

@dataclass(slots=True)
class SessionContext:
    pan_servo: PanServo
    settings: Settings
    storage_manager: StorageManager
    tilt_servo: TiltServo
    timer: Timer

class CaptureSession:
    """Class to store parameters for a PiKiteApp capture session."""
    def __init__(self, context: SessionContext):
        """
        Initialization for a PiKiteApp CaptureSession

        Args:
            app (PiKiteApp): The main PiKiteApp application instance.
            loop (bool): Flag to signal a capture session loop. Default is True.
        """
        self.context = context

        # Mark the start of the capture session for runtime tracking
        self.context.timer.mark("capture_session_start")
        self.session_start_time = datetime.now()
        
        # Determine capture mode based on application settings
        self.capture_mode = self._get_capture_mode()
        
        # Determine capture parameters based on capture mode
        self.media_extension = self._get_media_extension()
        self.video_length = self._get_video_length()
        self.capture_interval = self._get_capture_interval()

        # Create session directory to store captured media
        self.session_dir = self._get_session_dir()

        # Counter for captured media files in the current session
        self.capture_count = 0

        # Initialize altitude logging
        self.alt_csv, self.csv_writer = self._open_altitude_csv()
        self.altitude_interval = self.context.settings.get("altitude.interval", self.capture_interval)

        # Initialize pan/tilt pattern
        self.pan_tilt_pattern = self._create_pan_tilt_pattern()
        self.pan_tilt_interval = self.context.settings.get("pan_tilt.interval", 30)

    def __enter__(self):
        logger.debug("Entering CaptureSession context manager")
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug("Exiting CaptureSession context manager")
        self.close()
    
    def _get_capture_mode(self) -> CONSTANTS.CAPTURE_MODES:
        """Determine the capture mode based on application settings."""
        capture_mode_key = self.context.settings.get("capture.mode", "none")
        capture_mode = CONSTANTS.CAPTURE_MODES(capture_mode_key)
        if capture_mode is CONSTANTS.CAPTURE_MODES.NONE:
            logger.info("Capture mode is NONE; no media capture will be performed.")
        return capture_mode

    def _get_media_extension(self) -> CONSTANTS.MEDIA_EXTENSIONS | None:
        """Determine the media file extension based on the current capture mode."""
        if self.capture_mode == CONSTANTS.CAPTURE_MODES.STILL:
            return CONSTANTS.MEDIA_EXTENSIONS.JPG
        elif self.capture_mode == CONSTANTS.CAPTURE_MODES.VIDEO:
            return CONSTANTS.MEDIA_EXTENSIONS.MP4
        else:
            return None  # No media extension for NONE capture mode

    def _get_video_length(self) -> int:
        """Determine the video length based on the current capture mode."""
        if self.capture_mode == CONSTANTS.CAPTURE_MODES.VIDEO:
            return self.context.settings.get("capture.recording_duration", 15)
        else:
            return 0  # No video length for STILL or NONE capture modes

    def _get_capture_interval(self) -> int:
        """Determine the capture interval based on the current capture mode."""
        if self.capture_mode == CONSTANTS.CAPTURE_MODES.STILL:
            return self.context.settings.get("capture.interval", 2)
        elif self.capture_mode == CONSTANTS.CAPTURE_MODES.VIDEO:
            return self.context.settings.get("capture.interval", 30)
        else:
            return 2  # Default interval for NONE capture mode
        
    def _get_session_dir(self) -> Path | None:
        try:
            session_dir = self.context.storage_manager.new_session_dir(self.capture_mode)
        except ValueError as e:
            logger.warning(e)
            session_dir = None
        return session_dir

    def _open_altitude_csv(self) -> tuple:
        """Open a CSV file for logging altitude data."""
        alt_csv_path = self.context.storage_manager.get_data_file_path()
        alt_csv = open(alt_csv_path, "w", newline="")
        logger.info(f"Logging altitude data to: {alt_csv_path}")

        csv_writer = csv.writer(alt_csv)

        # Write CSV Header
        csv_writer.writerow(["Timestamp", "Altitude (m)"])

        return alt_csv, csv_writer
    
    def _create_pan_tilt_pattern(self) -> PanTiltPattern:
        """Create a PanTiltPattern instance based on application settings."""
        logger.debug(f"Creating pan/tilt pattern for capture session: {self.context.settings.get('pan_tilt.mode')}")
        pan_tilt_mode = PanTiltPattern.PAN_TILT_MODES(self.context.settings.get("pan_tilt.mode"))
        pan_tilt_pattern = PanTiltPattern(
            mode=pan_tilt_mode,
            pan_servo=self.context.pan_servo,
            tilt_servo=self.context.tilt_servo
        )
        return pan_tilt_pattern
    
    @property
    def runtime(self):
        """Calculate the runtime of the capture session."""
        return self.context.timer.since_mark("capture_session_start")

    @property
    def runtime_string(self):
        """Return the runtime as a formatted string."""
        return self.context.timer.format_elapsed_time(self.runtime)

    def get_info_payload(self):
        return {
            "type": "session_info",
            "session_start": self.session_start_time.strftime("%I:%M:%S %p"),
            "capture_mode": self.capture_mode.name,
            "media_type": self.media_extension.value if self.media_extension else None,
            "video_length": self.video_length,
            "capture_interval": self.capture_interval,
            "altitude_interval": self.altitude_interval,
            "pan_tilt_mode": self.pan_tilt_pattern.mode.name,
            "pan_tilt_interval": self.pan_tilt_interval
        }
    
    def get_update_payload(self):
        return {
            "type": "session_update",
            "capture_count": self.capture_count,
            "runtime": self.runtime_string,
        }

    def get_end_payload(self):
        return {
            "type": "session_end",
            "capture_count": self.capture_count,
            "final_runtime": self.runtime_string
        }

    def close(self):
        """Perform cleanup for the capture session."""
        try:
            # Close altitude CSV file
            self.alt_csv.close()
        except Exception:
            logger.exception("Failed to close the altitude CSV.")

        logger.info("Capture session closed. Cleanup complete.")