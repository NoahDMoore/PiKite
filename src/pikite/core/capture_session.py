import csv
from datetime import datetime
from typing import TYPE_CHECKING

import pikite.core.constants as CONSTANTS
from pikite.core.input_handler import InputCommand, InputScope
import pikite.core.logger as logger_module
from pikite.hardware.servo_controller import PanTiltPattern

if TYPE_CHECKING:
    from pikite.core.pikite_app import PiKiteApp

# Setup Logger
logger = logger_module.get_logger(__name__)

class CaptureSession:
    """Class to store parameters for a PiKiteApp capture session."""
    def __init__(self, app: "PiKiteApp", loop: bool = True):
        """
        Initialization for a PiKiteApp CaptureSession

        Args:
            app (PiKiteApp): The main PiKiteApp application instance.
            loop (bool): Flag to signal a capture session loop. Default is True.
        """
        self.app = app

        # Set flags for capture_loop logic
        self.loop = loop
        self.preparing_to_stop = False

        # Mark the start of the capture session for runtime tracking
        self.app.timer.mark("capture_session_start")
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
        self.altitude_interval = self.app.settings.get("alt_reading_interval", self.capture_interval)

        # Initialize pan/tilt pattern
        self.pan_tilt_pattern = self._create_pan_tilt_pattern()
        self.pan_tilt_interval = self.app.settings.get("pan_tilt_interval", 30)

        # Initialize handlers for remote session info requests
        self.info_handler = {
            "scope":InputScope.CAPTURE_LOOP,
            "command":InputCommand.REQUEST_SESSION_INFO,
            "callback":self.tx_session_info
        }

        self.app.input_handler.register(**self.info_handler)

        # Initialize media path arguments
        self.media_path_args = {
            "capture_mode":self.capture_mode,
            "media_extension":self.media_extension,
            "session_dir":self.session_dir
        }

        self.tx_session_info()  # Send initial session info to remote clients

    def __enter__(self):
        logger.debug("Entering CaptureSession context manager")
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        logger.debug("Exiting CaptureSession context manager")
        self.close()

    def _get_capture_mode(self) -> CONSTANTS.CAPTURE_MODES:
        """Determine the capture mode based on application settings."""
        capture_mode_key = self.app.settings.get("cam_capture_mode", "none")
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
            return self.app.settings.get("vid_length", 15)
        else:
            return 0  # No video length for STILL or NONE capture modes

    def _get_capture_interval(self) -> int:
        """Determine the capture interval based on the current capture mode."""
        if self.capture_mode == CONSTANTS.CAPTURE_MODES.STILL:
            return self.app.settings.get("pic_interval", 2)
        elif self.capture_mode == CONSTANTS.CAPTURE_MODES.VIDEO:
            return self.app.settings.get("vid_interval", 30)
        else:
            return 2  # Default interval for NONE capture mode
        
    def _get_session_dir(self):
        try:
            session_dir = self.app.storage_manager.new_session_dir(self.capture_mode)
        except ValueError as e:
            logger.warning(e)
            session_dir = None
        return session_dir

    def _open_altitude_csv(self) -> tuple:
        """Open a CSV file for logging altitude data."""
        alt_csv_path = self.app.storage_manager.get_data_file_path()
        alt_csv = open(alt_csv_path, "w", newline="")
        logger.info(f"Logging altitude data to: {alt_csv_path}")

        csv_writer = csv.writer(alt_csv)

        # Write CSV Header
        csv_writer.writerow(["Timestamp", "Altitude (m)"])

        return alt_csv, csv_writer
    
    def _create_pan_tilt_pattern(self) -> PanTiltPattern:
        """Create a PanTiltPattern instance based on application settings."""
        logger.debug(f"Creating pan/tilt pattern for capture session: {self.app.settings.get('pan_tilt_mode')}")
        pan_tilt_mode = PanTiltPattern.PAN_TILT_MODES(self.app.settings.get("pan_tilt_mode"))
        pan_tilt_pattern = PanTiltPattern(
            mode=pan_tilt_mode,
            pan_servo=self.app.pan_servo,
            tilt_servo=self.app.tilt_servo
        )
        return pan_tilt_pattern
    
    @property
    def runtime(self):
        """Calculate the runtime of the capture session."""
        return self.app.timer.since_mark("capture_session_start")

    @property
    def runtime_string(self):
        """Return the runtime as a formatted string."""
        return self.app.timer.format_elapsed_time(self.runtime)

    def tx_session_info(self):
        """Send capture session info to remote clients."""
        session_info_payload = {
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
        self.app.remote_server.send(session_info_payload)
    
    def tx_session_update(self):
        """Send capture session update to remote clients."""
        session_update_payload = {
            "type": "session_update",
            "scope": self.app.input_handler.active_scope.name,
            "capture_count": self.capture_count,
            "runtime": self.runtime_string,
            "is_recording": self.app.camera_controller.is_recording
        }
        self.app.remote_server.send(session_update_payload)

    def tx_session_end(self):
        """Send session end notification to remote clients."""
        session_end_payload = {
            "type": "session_end",
            "capture_count": self.capture_count,
            "final_runtime": self.runtime_string
        }
        self.app.remote_server.send(session_end_payload)

    def close(self):
        """Perform cleanup for the capture session."""
        # Close altitude CSV file
        self.alt_csv.close()
        
        # TX final session update to remote clients to indicate capture loop has ended
        self.tx_session_end()

        # Unregister capture loop specific input handlers
        self.app.input_handler.unregister(**self.info_handler)

        logger.info("Capture session closed. Cleanup complete.")