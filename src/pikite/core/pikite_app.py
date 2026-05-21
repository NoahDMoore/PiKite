import asyncio
import csv
from datetime import datetime

import pikite.core.constants as CONSTANTS
from pikite.core.input_handler import InputHandler, InputCommand, InputScope, RemoteInput
from pikite.core.lcd_menu import Menu
import pikite.core.logger as logger_module
from pikite.core.settings import Settings
from pikite.core.timer import Timer
from pikite.hardware import display_controller
from pikite.hardware.camera_controller import CameraController
from pikite.hardware.button_controller import ButtonController
from pikite.hardware.display_controller import DisplayController, LoadingBar, PreLoader
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.servo_controller import TiltServo, PanServo, PanTiltPattern
from pikite.remote.microdot_server import ControllerServer
from pikite.system.storage import StorageManager, get_timestamp
import pikite.system.power_management as PowerManagement
from ..system.system_info import display_system_info

# Setup Logger
logger = logger_module.get_logger(__name__)

class PiKiteApp:
    def __init__(self):
        # Initialize Display
        self.display_controller = DisplayController()
        initialization_progress_bar = LoadingBar("Loading PiKite", self.display_controller)
        initialization_progress_bar.advance(10)
        
        # Initialize Timer
        self.timer = Timer()
        self.timer.start()
        initialization_progress_bar.advance(10)

        # Initialize Storage Manager
        self.storage_manager = StorageManager()
        initialization_progress_bar.advance(10)

        # Load Settings
        self.settings = Settings()
        self.settings.add_change_listener(self._on_setting_change)
        initialization_progress_bar.advance(10)

        # Configure Logger from Settings
        self.configure_logger()
        initialization_progress_bar.advance(10)

        # Initialize Sensors
        self.pressure_sensor = PressureSensorController()
        initialization_progress_bar.advance(5)

        self.camera_controller = CameraController(self.settings)
        initialization_progress_bar.advance(5)

        # Initialize Servo Controllers
        offset = int(self.settings.get("pan_tilt_zero_angle_offset", 0))
        self.tilt_servo = TiltServo(zero_angle_offset=offset) # Adjust zero angle offset to ensure camera is level when tilt angle is set to 0
        initialization_progress_bar.advance(5)

        self.pan_servo = PanServo()
        initialization_progress_bar.advance(5)

        # Initialize Input Handler
        self.input_handler = InputHandler()
        initialization_progress_bar.advance(10)

        # Initialize Remote Controller Server
        self.remote_server = ControllerServer(port=5000)
        
        # Initialize Remote Input Handler
        self.remote_input = RemoteInput(self.remote_server, self.input_handler)
        self.register_remote_handlers()
        initialization_progress_bar.advance(10)

        # Initialize Buttons
        self.button_controller = self.initialize_button_input()
        initialization_progress_bar.advance(10)

        # Run Preloader Animation
        preloader = PreLoader(self.display_controller)
        preloader.play()

        # Initialize Menu System
        self.menu = self.initialize_menu()

        # Session Variables
        self.capturing = False

        logger.info("PiKite Application Initialized")

    def _on_setting_change(self, setting_key, section, new_value):
        logger.info(f"Setting Change Detected: {setting_key} changed to {new_value} in section {section}")
        
        if section == "logging_settings":
            self.configure_logger()
            logger.info("Logger reconfigured due to logging settings change.")

        if section == "camera_settings":
            self.camera_controller.reconfigure_camera()
            self.timer.wait(0.5) # Small delay to allow camera to reconfigure before use
            logger.info("Camera controller reconfigured due to camera settings change.")

        if setting_key == "pan_tilt_zero_angle_offset":
            self.tilt_servo.zero_angle_offset = new_value
            logger.info(f"Updated tilt servo zero angle offset to {new_value} due to settings change.")

    def configure_logger(self):
        """
        Configure the logger based on application settings.

        Args:
            settings (Settings): Application settings.
        """
        log_level = self.settings.get("log_level", "INFO")
        logger_module.set_log_level(log_level)
        logger.info(f"Log level set to {log_level}")

        if self.settings.get("log_to_file", True) is False:
            logger.info("Logging to file disabled via settings.")
            logger_module.unset_file_handler()
        
        if self.settings.get("log_to_console", True) is False:
            logger.info("Logging to console disabled via settings.")
            logger_module.unset_stream_handler()

    def initialize_button_input(self) -> ButtonController:
        """
        Initialize the ButtonController for GPIO input handling.

        Returns:
            ButtonController: The initialized button controller instance.
        """
        button_controller = ButtonController(self.input_handler)
        self.input_handler.add_scope_change_listener(button_controller.sync_scope)
        
        button_controller.set_commands(
            next_command=InputCommand.NEXT,
            select_command=InputCommand.SELECT,
            scope=InputScope.MENU
        )
        
        button_controller.set_commands(
            next_command=InputCommand.STOP_CAPTURE,
            select_command=InputCommand.STOP_CAPTURE,
            scope=InputScope.CAPTURE_LOOP
        )

        return button_controller
    
    async def system_info(self):
        display_system_info(self.display_controller) # type: ignore
        await asyncio.sleep(4)

    def initialize_menu(self) -> Menu:
        """
        Initialize the menu system and register input commands.

        Args:
            settings (Settings): Application settings.
            display_controller (DisplayController): The display controller instance.
            input_handler (InputHandler): The input handler instance.

        Returns:
            Menu: The initialized menu instance.
        """
        menu = Menu(self.display_controller, self.settings, self.input_handler) #type: ignore

        self.input_handler.set_scope(InputScope.MENU)

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.NEXT,
            callback=menu.increment_element
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.SELECT,
            callback=menu.do_action
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.START_CAPTURE,
            callback=lambda: self.input_handler.set_scope(InputScope.CAPTURE_LOOP)
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.DISPLAY_SYSTEM_INFO,
            callback=lambda: asyncio.create_task(self.system_info())
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.SHUTDOWN,
            callback=PowerManagement.shutdown
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.REBOOT,
            callback=PowerManagement.reboot
        )

        return menu

    """Remote Command Handlers"""

    def tx_settings(self, **kwargs):
        """Fetch current settings and menu options to send to remote clients."""
        current_settings = self.settings.format_as_dict()
        menu_settings = self.menu.format_settings_and_options_as_dict()
        settings_payload = {
            "type": "settings_update",
            "current_settings": current_settings,
            "menu_settings": menu_settings
        }

        self.remote_server.send(settings_payload)
        logger.debug("Sent current settings and menu options to remote clients")

    def rx_settings_update(self, args):
        for new_setting, new_setting_value in args.get("settings_to_update", {}).items():
            if self.settings.is_setting(new_setting):
                logger.debug(f"Remotely updating setting '{new_setting}' from {self.settings.get(new_setting)} to new value '{new_setting_value}'")
                self.settings.set(new_setting, new_setting_value)
                self.tx_settings()  # Send updated settings back to client
            else:
                logger.info(f"Remote user attempted to update unknown setting: {new_setting}")

    def rx_default_settings_request(self, **kwargs):
        self.settings.load_defaults()
        self.tx_settings()  # Send updated settings back to client

    def tx_media_dirs(self, **kwargs):
        media_dirs = self.storage_manager.get_capture_session_dirs()
        media_dirs_payload = {
            "type": "media_dirs_update",
            "media_dirs": media_dirs
        }
        self.remote_server.send(media_dirs_payload)

    def tx_media_file_paths(self, args):
        mode = CONSTANTS.CAPTURE_MODES.STILL if args.get("mode") == "STILL" else CONSTANTS.CAPTURE_MODES.VIDEO
        path = args.get("path")
        file_paths = self.storage_manager.get_capture_session_file_names(mode, path)
        file_paths_payload = {
            "type": "media_file_paths",
            "file_paths": file_paths
        }
        self.remote_server.send(file_paths_payload)

    def register_remote_handlers(self):
        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.FETCH_SETTINGS,
            callback=self.tx_settings
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.UPDATE_SETTINGS,
            callback=self.rx_settings_update
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.LOAD_DEFAULT_SETTINGS,
            callback=self.rx_default_settings_request
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.FETCH_MEDIA_DIRS,
            callback=self.tx_media_dirs
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.FETCH_MEDIA,
            callback=self.tx_media_file_paths
        )

        self.input_handler.register(
            scope=InputScope.CAPTURE_LOOP,
            command=InputCommand.STOP_CAPTURE,
            callback=lambda: self.input_handler.set_scope(InputScope.MENU)
        )

    """Capture Loop Helper Methods"""

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

    def home_pan_tilt(self):
        self.pan_servo.rotate_to(speed=0.5, target_angle=0)
        self.tilt_servo.angle = 0
        logger.info("Pan/Tilt homed to default position")

    @property
    def is_recording(self):
        return self.camera_controller.is_recording

    async def capture_loop(self):
        """
        Main capture loop for handling image capture and processing.
        """
        try:
            logger.info("Starting Capture Loop")
            self.capturing = True   # Set capturing flag to True at the start of the loop

            with CaptureSession(self) as session:
                self.pressure_sensor.get_baseline_pressure(num_samples=80, display_controller=self.display_controller)

                while self.capturing or self.is_recording:
                    if self.input_handler.active_scope != InputScope.CAPTURE_LOOP:
                        self.capturing = False

                    if self.timer.interval_elapsed(1.0, "runtime"):
                        self.display_controller.print_message(f"PiKite Running: {session.runtime_string}")

                    if self.timer.interval_elapsed(session.altitude_interval, "altitude_interval"):
                        self.log_altitude(session.csv_writer)

                    if self.timer.interval_elapsed(session.capture_interval, "capture_interval") and not self.is_recording:
                        # Get media path for capture
                        media_path = self.get_media_path(**session.media_path_args)

                        # Capture media based on mode
                        match session.capture_mode:
                            case CONSTANTS.CAPTURE_MODES.NONE:
                                pass # Do Nothing if the capture mode is set to None
                            case CONSTANTS.CAPTURE_MODES.STILL:
                                self.capture_photo(media_path)
                                session.capture_count += 1
                            case CONSTANTS.CAPTURE_MODES.VIDEO:
                                self.start_video(media_path)
                                self.timer.set_named_interval("video_length")
                                
                    if self.is_recording:
                        if self.timer.interval_elapsed(session.video_length, "video_length"):
                            self.stop_video()
                            session.capture_count += 1
                            self.timer.set_named_interval("capture_interval")
                            self.timer.named_intervals.pop("video_length", None)  # Clear video length interval

                        # If capture has been stopped but video is still recording, log time remaining until recording stops
                        if not self.capturing:
                            if self.timer.interval_elapsed(1.0, "time_remaining_check"):
                                time_remaining = self.timer.interval_remaining(session.video_length, "video_length")
                                logger.info("Capture loop ending, but video is still recording. Waiting for recording to finish... {time_remaining:.1f}s remaining.")

                    if self.timer.interval_elapsed(session.pan_tilt_interval, "pan_tilt_interval") and not self.is_recording:
                        await self.step_pan_tilt(session.pan_tilt_pattern)

                    # Update session info on remote clients at regular intervals
                    if self.timer.interval_elapsed(1.0, "session_info_update"):
                        session.tx_session_update()

                    await asyncio.sleep(0.01)
        finally:
            logger.info("Exiting Capture Loop, performing cleanup")

            # Clear Capture Intervals
            for key in ["runtime", "capture_interval", "altitude_interval", "pan_tilt_interval", "time_remaining_check", "session_info_update"]:
                self.timer.named_intervals.pop(key, None)

            # Home the Pan/Tilt Servos
            self.home_pan_tilt()

            # Reset input scope to MENU when capture loop exits
            self.input_handler.set_scope(InputScope.MENU)   # Ensure scope is reset to MENU when capture loop exits
            self.menu.update_menu()

    async def main_loop(self):
        application_running = True
        while application_running:
            await asyncio.sleep(0.1)
            if self.input_handler.active_scope == InputScope.MENU:
                pass
            elif self.input_handler.active_scope == InputScope.CAPTURE_LOOP:
                await self.capture_loop()

        # Cleanup at End of Runtime
        self.button_controller.cleanup()

    async def run(self):
        logger.info("Starting PiKite Application")

        await asyncio.gather(
            self.remote_server.start(),
            self.remote_input.start_listening(),
            self.main_loop()
        )

class CaptureSession:
    """Class to manage state and parameters for a media capture session."""
    def __init__(self, app: PiKiteApp):
        self.app = app

        # Mark the start of the capture session for runtime tracking
        self.app.timer.mark("capture_loop_start")
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
        return self.app.timer.since_mark("capture_loop_start")

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