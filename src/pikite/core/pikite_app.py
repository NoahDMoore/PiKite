import asyncio
from typing import Callable
from inspect import isawaitable

from pikite.core.capture_manager import CaptureManager
import pikite.core.constants as CONSTANTS
from pikite.core.input_handler import InputHandler, InputCommand, InputScope, RemoteInput
from pikite.core.lcd_menu import Menu
import pikite.utils.logger as logger_module
from pikite.core.settings import Settings
from pikite.utils.timer import Timer
from pikite.hardware.camera_controller import CameraController, PreviewStream
from pikite.hardware.button_controller import ButtonController
from pikite.hardware.display_controller import DisplayController, LoadingBar, PreLoader
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.servo_controller import TiltServo, PanServo
from pikite.remote.microdot_server import ControllerServer
from pikite.system.storage import StorageManager
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

        # Initialize CaptureManager
        self.capture_manager = CaptureManager(
            camera_controller=self.camera_controller,
            display_controller=self.display_controller,
            input_handler=self.input_handler,
            pan_servo=self.pan_servo,
            pressure_sensor=self.pressure_sensor,
            remote_server=self.remote_server,
            settings=self.settings,
            tilt_servo=self.tilt_servo,
        )

        # Run Preloader Animation
        preloader = PreLoader(self.display_controller)
        preloader.play()

        # Initialize Menu System
        self.menu = self.initialize_menu()

        logger.info("PiKite Application Initialized")

        self.application_running = False
        self.on_close_callback = None

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

        for scope in [InputScope.MENU, InputScope.SYSTEM_INFO]:
            self.input_handler.register(
                scope=scope,
                command=InputCommand.SHUTDOWN,
                callback=self.shutdown
            )

            self.input_handler.register(
                scope=scope,
                command=InputCommand.REBOOT,
                callback=self.reboot
            )

            self.input_handler.register(
                scope=scope,
                command=InputCommand.EXIT,
                callback=self.exit
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

    def tx_scope(self):
        """Transmit the current scope to remote clients"""
        scope_payload = {
            "type": "scope_update",
            "scope": self.input_handler.active_scope
        }

        self.remote_server.send(scope_payload)
        logger.debug("Sent current settings and menu options to remote clients")

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
        self.input_handler.add_scope_change_listener(self.tx_scope)

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

    async def main_loop(self):
        self.application_running = True
        try:
            self.preview.start()

            while self.application_running:
                if self.input_handler.active_scope == InputScope.MENU:
                    pass

                elif self.input_handler.active_scope == InputScope.CAPTURE_LOOP:
                    await self.preview.stop()

                    await self.capture_manager.capture_loop()
                    
                    await asyncio.sleep(2)

                    self.preview.start()

                    self.input_handler.set_scope(InputScope.MENU)

                elif self.input_handler.active_scope == InputScope.SYSTEM_INFO:
                    display_system_info(self.display_controller) # type: ignore

                    while self.input_handler.active_scope == InputScope.SYSTEM_INFO:
                        await asyncio.sleep(0.1)

                await asyncio.sleep(0.1)
        finally:
            await self.cleanup()

    async def run(self):
        logger.info("Starting PiKite Application")

        self.remote_server.start()
        
        await asyncio.gather(
            self.remote_input.start_listening(),
            self.preview.stream(),
            self.main_loop()
        )

        self.on_close()

    def register_on_close_callback(self, callback: Callable):
        self.on_close_callback = callback

    def on_close(self):
        if self.on_close_callback is not None and isinstance(self.on_close_callback, Callable):
            self.on_close_callback()

    def exit(self):
        self.application_running = False

    def shutdown(self):
        self.register_on_close_callback(PowerManagement.shutdown)
        self.exit()

    def reboot(self):
        self.register_on_close_callback(PowerManagement.reboot)
        self.exit()

    async def cleanup(self):
        # Cleanup at End of Runtime
        logger.info("Preparing to close PiKite. Cleaning up...")

        # Create Progress Bar to Display Cleanup Progress
        try:
            cleanup_progress_bar = LoadingBar("Closing PiKite", self.display_controller)
        except TypeError:
            cleanup_progress_bar = None
        
        # Advance the Progress Bar (if it exists)
        def _advance_progress():
            if cleanup_progress_bar is not None:
                cleanup_progress_bar.advance(10)

        async def _cleanup_servos():
            # Home the Servos
            self.pan_servo.home()
            await asyncio.sleep(0.1)
            self.tilt_servo.home()
            await asyncio.sleep(0.1)

            # Stop the Pan Servo
            self.pan_servo.stop()

            # Stop the Tilt Servo
            self.tilt_servo.stop()

        def _cleanup_timer():
            runtime = self.timer.stop()
            logger.info(f"PiKite has run for {self.timer.format_elapsed_time(runtime)}.")

        def _cleanup_display_controller():
            self.display_controller.print_message(
                message="PiKite Closed",
                bg_color=(0,0,0),
                fg_color=(255,255,255)
            )

            # Cleanup Display Controller
            self.display_controller.close()

        # Define Cleanup Steps
        cleanup_tasks = [
            self.button_controller.close,   # Cleanup Button Controller
            self.preview.close,             # Cleanup Camera Preview Stream
            self.remote_input.close,        # Cleanup RemoteInput
            self.remote_server.close,       # Shutdown ControllerServer
            _cleanup_servos,                # Home and Then Stop the Pan and Tilt Servos
            self.camera_controller.close,   # Cleanup Camera Controller
            _cleanup_timer,                 # Stop the Timer and Log Runtime
            _cleanup_display_controller     # Cleanup Display Controller
        ]

        # Call Each Cleanup Task
        for i, task in enumerate(cleanup_tasks):
            try:
                result = task()

                if isawaitable(result):
                    await result
            except Exception as e:
                logger.error(f"Failed to execute cleanup task {task.__name__ if hasattr(task, '__name__') else task}: {e}")
            finally:
                # Do not advance the progress bar on last iteration since the display_controller has been shutdown.
                if i == (len(cleanup_tasks) - 1):
                    break
                
                # Advance the progress bar
                _advance_progress()

        logger.info("PiKite clean-up complete. Closing application.")

    