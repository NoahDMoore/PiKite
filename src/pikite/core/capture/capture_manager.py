import asyncio
from enum import Enum, auto
from pathlib import Path

from pikite.core.capture.capture_session import SessionContext, CaptureSession
from pikite.core.constants import CAPTURE_MODES
from pikite.core.settings import Settings
from pikite.hardware.camera.camera_controller import CameraController
from pikite.hardware.display.display_controller import DisplayController
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.servos.pan_servo import PanServo
from pikite.hardware.servos.tilt_servo import TiltServo
from pikite.remote.remote_api import RemoteAPI
from pikite.system.storage import StorageManager, get_timestamp
import pikite.utils.logger as logger_module
from pikite.utils.timer import Timer

# Setup Logger
logger = logger_module.get_logger(__name__)

class CaptureState(Enum):
    RUNNING = auto()
    STOP_REQUESTED = auto()
    STOPPING = auto()
    STOPPED = auto()

class CaptureManager:
    def __init__(
        self,
        camera_controller: CameraController,
        display_controller: DisplayController,
        pan_servo: PanServo,
        pressure_sensor: PressureSensorController,
        remote_api: RemoteAPI,
        settings: Settings,
        tilt_servo: TiltServo
    ):
        self.camera_controller = camera_controller
        self.display_controller = display_controller
        self.pressure_sensor = pressure_sensor
        self.remote_api = remote_api
        self.tilt_servo = tilt_servo
        self.timer = Timer()
        self.timer.start()
        self.storage_manager = StorageManager()
        self.state = CaptureState.STOPPED

        self.session_context = SessionContext(
            pan_servo = pan_servo,
            settings = settings,
            tilt_servo = self.tilt_servo,
            timer = self.timer,
        )

        self._current_session: CaptureSession | None = None

    def _register_session(self, session: CaptureSession):
        if not isinstance(session, CaptureSession):
            logger.error("Session must be of type CaptureSession")
            return
        
        self._current_session = session

    def get_current_session(self) -> CaptureSession | None:
        if isinstance(self._current_session, CaptureSession):
            return self._current_session
        else:
            return None
    
    def capture_photo(self, media_path: Path):
        """
        Capture a photo and send the file path to remote clients.
        
        Args:
            media_path (Path): The file path where the captured photo will be saved.
            session_dir (Path): The directory where the capture session is stored.
        """
        self.camera_controller.capture_image(media_path)
        logger.info(f"Captured photo: {media_path}")
        self.remote_api.tx_last_captured_photo(media_path)

    def start_video(self, media_path: Path):
        self.camera_controller.start_video(media_path)
        logger.info(f"Started video recording: {media_path}")

    def stop_video(self):
        if self.is_recording:
            self.camera_controller.stop_video()
            logger.info("Stopped video recording")

    def log_altitude(self, csv_writer):
        altitude = self.pressure_sensor.altitude
        timestamp = get_timestamp()
        csv_writer.writerow([timestamp, altitude])

        logger.debug(f"Logged altitude: {altitude} at {timestamp}")

        self.remote_api.tx_altitude(altitude, timestamp)

    async def step_pan_tilt(self, pan_tilt_pattern):
        pan_tilt_pattern.step()
        await asyncio.sleep(0.5) # Small delay to allow servo movement before next step
        logger.debug("Pan/tilt step executed")

        pan_angle = pan_tilt_pattern.current_pan_angle
        self.remote_api.tx_servo_positions(pan_angle)

    def request_stop(self):
        if self.state != CaptureState.RUNNING:
            logger.warning("Cannot request stop. PiKite is not running a capture loop.")
            return
        
        self.state = CaptureState.STOP_REQUESTED

    @property
    def is_recording(self):
        return self.camera_controller.is_recording

    async def capture_loop(self):
        """
        Main capture loop for handling image capture and processing.
        """
        try:
            logger.info("Starting Capture Loop")
            self.state = CaptureState.RUNNING

            with CaptureSession(self.session_context) as session:
                self._register_session(session)

                # Transmit Initial Session Info
                self.remote_api.tx_session_info(session)

                while True:
                    if self.timer.interval_elapsed(1.0, "runtime_and_session_info"):
                        self.display_controller.put(f"PiKite Running:\n{session.runtime_string}")
                        self.remote_api.tx_session_update(session) # Send session update to remote client

                    if self.timer.interval_elapsed(session.altitude_interval, "altitude_interval"):
                        self.log_altitude(session.csv_writer)

                    if self.timer.interval_elapsed(session.capture_interval, "capture_interval") and not self.is_recording:
                        # Get media path for capture
                        media_path = self.storage_manager.media_file_path(
                            mode=session.capture_mode,
                            extension=session.media_extension,
                            session_dir=session.session_dir    
                        )

                        # Capture media based on mode
                        match session.capture_mode:
                            case CAPTURE_MODES.NONE:
                                pass # Do Nothing if the capture mode is set to None
                            case CAPTURE_MODES.STILL:
                                self.capture_photo(media_path)
                                session.capture_count += 1
                            case CAPTURE_MODES.VIDEO:
                                self.start_video(media_path)
                                self.timer.set_named_interval("video_length")
                                
                    if self.is_recording:
                        # If capture has been stopped but video is still recording, log time remaining until recording stops
                        if self.state == CaptureState.STOP_REQUESTED:
                            if self.timer.interval_elapsed(1.0, "time_remaining_check"):
                                time_remaining = self.timer.interval_remaining(session.video_length, "video_length")
                                logger.info(f"Capture loop ending, but video is still recording. Waiting for recording to finish... {time_remaining:.1f}s remaining.")
                        
                        if self.timer.interval_elapsed(session.video_length, "video_length"):
                            self.stop_video()
                            session.capture_count += 1
                            self.timer.set_named_interval("capture_interval")
                            self.timer.named_intervals.pop("video_length", None)  # Clear video length interval

                    if self.timer.interval_elapsed(session.pan_tilt_interval, "pan_tilt_interval") and not self.is_recording:
                        await self.step_pan_tilt(session.pan_tilt_pattern)

                    if self.state == CaptureState.STOP_REQUESTED and not self.is_recording:
                        self.state = CaptureState.STOPPING
                        break

                    await asyncio.sleep(0.01)
                
                # Transmit Session End Payload After Loop Ends
                try:
                    self.remote_api.tx_session_end(session)
                except Exception:
                    logger.exception("Failed to transmit session end payload.")
        finally:
            logger.info("Exiting Capture Loop, performing cleanup")

            # Clear Capture Intervals
            for key in [
                "runtime_and_session_info",
                "capture_interval",
                "altitude_interval",
                "pan_tilt_interval",
                "time_remaining_check"
            ]:
                self.timer.named_intervals.pop(key, None)

            # Home the Pan/Tilt Servos and Reset Session
            if self._current_session is not None:
                self._current_session.pan_tilt_pattern.reset()
                self._current_session = None

            self.state = CaptureState.STOPPED