import asyncio
from enum import Enum, auto

from pikite.core.capture_session import SessionContext, CaptureSession
from pikite.core.constants import PiKiteMode, CAPTURE_MODES
from pikite.core.input_handler import InputHandler, InputCommand
import pikite.utils.logger as logger_module
from pikite.core.settings import Settings
from pikite.utils.timer import Timer
from pikite.hardware.camera_controller import CameraController
from pikite.hardware.display_controller import DisplayController
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.servo_controller import TiltServo, PanServo
from pikite.remote.microdot_server import ControllerServer
from pikite.system.storage import StorageManager, get_timestamp

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
        input_handler: InputHandler,
        pan_servo: PanServo,
        pressure_sensor: PressureSensorController,
        remote_server: ControllerServer,
        settings: Settings,
        tilt_servo: TiltServo
    ):
        self.camera_controller = camera_controller
        self.display_controller = display_controller
        self.input_handler = input_handler
        self.pan_servo = pan_servo
        self.pressure_sensor = pressure_sensor
        self.remote_server = remote_server
        self.settings = settings
        self.storage_manager = StorageManager()
        self.tilt_servo = tilt_servo
        self.timer = Timer()
        self.timer.start()
        self.state = CaptureState.STOPPED

        self.session_context = SessionContext(
            self.pan_servo,
            self.settings,
            self.storage_manager,
            self.tilt_servo,
            self.timer,
        )

        # Register Handler for Stop command
        self.input_handler.register(
            mode=PiKiteMode.CAPTURE_LOOP,
            command=InputCommand.STOP_CAPTURE,
            callback=self._request_stop
        )

    def get_media_path(self, capture_mode, media_extension, session_dir):
        if media_extension:
            return self.storage_manager.media_file_path(
                mode=capture_mode, 
                extension=media_extension,
                session_dir=session_dir
            )
        return None
    
    def capture_photo(self, media_path):
        """
        Capture a photo and send the file path to remote clients.
        
        Args:
            media_path (Path): The file path where the captured photo will be saved.
            session_dir (Path): The directory where the capture session is stored.
        """
        self.camera_controller.capture_image(media_path)
        logger.info(f"Captured photo: {media_path}")
        self.tx_last_captured_photo(media_path)

    def tx_last_captured_photo(self, media_path):
        """Send the obfuscated file path of the last captured photo to remote clients."""
        file_path = f"/media/{self.storage_manager.PHOTO_OUTPUT_DIR.name}/{media_path.parent.name}/{media_path.name}"
        file_paths_payload = {
            "type": "last_captured_photo",
            "file_path": file_path
        }
        self.remote_server.send(file_paths_payload)

    def start_video(self, media_path):
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

        self.remote_server.send({
            "type": "altitude_update",
            "altitude": altitude,
            "timestamp": timestamp
        })

    async def step_pan_tilt(self, pan_tilt_pattern):
        pan_tilt_pattern.step()
        await asyncio.sleep(0.5) # Small delay to allow servo movement before next step
        logger.debug("Pan/tilt step executed")

        self.remote_server.send({
            "type": "pan_tilt_update",
            "pan_angle": pan_tilt_pattern.current_pan_angle,
            "tilt_angle": self.tilt_servo.angle
        })

    def _request_stop(self):
        if self.state != CaptureState.RUNNING:
            logger.warning("Cannot request stop. PiKite is not running a capture loop.")
            return
        
        self.state = CaptureState.STOP_REQUESTED

    @property
    def is_recording(self):
        return self.camera_controller.is_recording
    
    def tx_session_info(self, session: CaptureSession):
        """Send capture session info to remote clients."""
        self.remote_server.send(session.get_info_payload())
    
    def tx_session_update(self, session: CaptureSession):
        """Send capture session update to remote clients."""
        self.remote_server.send(session.get_update_payload())

    def tx_session_end(self, session: CaptureSession):
        """Send session end notification to remote clients."""
        self.remote_server.send(session.get_end_payload())

    async def capture_loop(self):
        """
        Main capture loop for handling image capture and processing.
        """
        try:
            logger.info("Starting Capture Loop")
            self.state = CaptureState.RUNNING

            with CaptureSession(self.session_context) as session:
                # Transmit Initial Session Info
                self.tx_session_info(session)

                # Register Handler for Session Info Requests
                self._info_handler = {
                    "mode":PiKiteMode.CAPTURE_LOOP,
                    "command":InputCommand.REQUEST_SESSION_INFO,
                    "callback":lambda: self.tx_session_info(session)
                }
                self.input_handler.register(**self._info_handler)

                while True:
                    if self.timer.interval_elapsed(1.0, "runtime_and_session_info"):
                        self.display_controller.print_message(f"PiKite Running: {session.runtime_string}")
                        self.tx_session_update(session) # Send session update to remote client

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
                    self.tx_session_end(session)
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

            # Home the Pan/Tilt Servos
            self.pan_servo.home()
            await asyncio.sleep(0.1)
            self.tilt_servo.home()
            await asyncio.sleep(0.1)

            # Unregister capture loop specific input handlers
            self.input_handler.unregister(**self._info_handler)

            self.state = CaptureState.STOPPED