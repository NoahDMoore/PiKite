import asyncio

from pikite.core.capture_session import CaptureSession
import pikite.core.constants as CONSTANTS
from pikite.core.input_handler import InputHandler, InputCommand, InputScope, RemoteInput
from pikite.core.lcd_menu import Menu
import pikite.core.logger as logger_module
from pikite.core.settings import Settings
from pikite.core.timer import Timer
from pikite.hardware.camera_controller import CameraController, PreviewStream
from pikite.hardware.button_controller import ButtonController
from pikite.hardware.display_controller import DisplayController, LoadingBar, PreLoader
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.servo_controller import TiltServo, PanServo
from pikite.remote.microdot_server import ControllerServer
from pikite.system.storage import StorageManager, get_timestamp
import pikite.system.power_management as PowerManagement
from pikite.system.system_info import display_system_info

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

        # Initialize Camera Preview Stream
        self.preview = PreviewStream(self.camera_controller, self.remote_server)
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

        button_controller.set_commands(
            next_command=InputCommand.NEXT,
            select_command=InputCommand.SELECT,
            scope=InputScope.SYSTEM_INFO
        )

        return button_controller
    
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

        self.input_handler.add_scope_change_listener(self._on_enter_menu_scope)

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
            command=InputCommand.SET_BASELINE_PRESSURE,
            callback=lambda: self.pressure_sensor.get_baseline_pressure(
                num_samples=80,
                display_controller=self.display_controller
            )
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.DISPLAY_SYSTEM_INFO,
            callback=lambda: self.input_handler.set_scope(InputScope.SYSTEM_INFO)
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

        self.input_handler.register(
            scope=InputScope.SYSTEM_INFO,
            command=InputCommand.NEXT,
            callback=lambda: self.input_handler.set_scope(InputScope.MENU)
        )

        self.input_handler.register(
            scope=InputScope.SYSTEM_INFO,
            command=InputCommand.SELECT,
            callback=lambda: self.input_handler.set_scope(InputScope.MENU)
        )

        return menu
    
    def _on_enter_menu_scope(self, new_scope: InputScope):
        if not new_scope == InputScope.MENU:
            return
        self.menu.update_menu()


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

    def rx_pan_command(self, args):
        angle = args.get("angle")
        self.pan_servo.rotate_to(
            speed = 0.5,
            target_angle = int(angle),
            margin = 4
        )
        self.timer.wait(0.5)

    def rx_tilt_command(self, args):
        angle = args.get("angle")
        self.tilt_servo.angle = int(angle)
        self.timer.wait(0.5)

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
            scope=InputScope.MENU,
            command=InputCommand.PAN,
            callback=self.rx_pan_command
        )

        self.input_handler.register(
            scope=InputScope.MENU,
            command=InputCommand.TILT,
            callback=self.rx_tilt_command
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
                while self.capturing or self.is_recording:
                    if self.input_handler.active_scope != InputScope.CAPTURE_LOOP:
                        self.capturing = False

                    if self.timer.interval_elapsed(1.0, "runtime_and_session_info"):
                        self.display_controller.print_message(f"PiKite Running: {session.runtime_string}")
                        session.tx_session_update() # Send session update to remote client

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
                                logger.info(f"Capture loop ending, but video is still recording. Waiting for recording to finish... {time_remaining:.1f}s remaining.")

                    if self.timer.interval_elapsed(session.pan_tilt_interval, "pan_tilt_interval") and not self.is_recording:
                        await self.step_pan_tilt(session.pan_tilt_pattern)

                    await asyncio.sleep(0.01)
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
            self.home_pan_tilt()

    async def main_loop(self):
        application_running = True
        self.preview.start()

        while application_running:
            if self.input_handler.active_scope == InputScope.MENU:
                pass

            elif self.input_handler.active_scope == InputScope.CAPTURE_LOOP:
                self.preview.stop()

                await self.capture_loop()
                await asyncio.sleep(2)
                self.preview.start()

            elif self.input_handler.active_scope == InputScope.SYSTEM_INFO:
                display_system_info(self.display_controller) # type: ignore

                while self.input_handler.active_scope == InputScope.SYSTEM_INFO:
                    await asyncio.sleep(0.1)

            await asyncio.sleep(0.1)
            
        # Cleanup at End of Runtime
        self.button_controller.cleanup()
        self.preview.stop()

    async def run(self):
        logger.info("Starting PiKite Application")

        await asyncio.gather(
            self.remote_server.start(),
            self.remote_input.start_listening(),
            self.preview.stream(),
            self.main_loop()
        )