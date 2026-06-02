import asyncio
from typing import Callable
from inspect import isawaitable

from pikite.core.modes.baseline_altitude_mode import BaselineAltitudeMode
from pikite.core.modes.capture_mode import CaptureMode
from pikite.core.modes.menu_mode import MenuMode
from pikite.core.modes.mode_manager import ModeManager
from pikite.core.modes.pikite_mode import PiKiteMode
from pikite.core.modes.system_info_mode import SystemInfoMode
from pikite.core.capture_manager import CaptureManager
from pikite.core.input_handler import InputHandler, RemoteInput
from pikite.core.menu import Menu
import pikite.utils.logger as logger_module
from pikite.core.settings import Settings
from pikite.utils.timer import Timer
from pikite.hardware.camera_controller import CameraController, PreviewStream
from pikite.hardware.button_controller import ButtonController
from pikite.hardware.display_controller import DisplayController, LoadingBar, PreLoader
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.servo_controller import TiltServo, PanServo
from pikite.remote.remote_server import RemoteServer
from pikite.remote.remote_api import RemoteAPI
from pikite.system.storage import StorageManager
import pikite.system.power_management as PowerManagement

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

        # Initialize Menu System
        self.menu = Menu(self.display_controller, self.settings, self.input_handler) #type: ignore

        # Initialize Remote Controller Server
        self.remote_server = RemoteServer(port=5000)
        
        # Initialize Remote Input Handler
        self.remote_input = RemoteInput(self.remote_server, self.input_handler)
        self.remote_api = RemoteAPI(
            menu=self.menu,
            pan_servo=self.pan_servo,
            remote_server=self.remote_server,
            settings=self.settings,
            storage_manager=self.storage_manager,
            tilt_servo=self.tilt_servo
        )

        # Initialize Camera Preview Stream
        self.preview = PreviewStream(self.camera_controller, self.remote_server)
        initialization_progress_bar.advance(10)

        # Initialize Buttons
        self.button_controller = ButtonController(self.input_handler)
        self.input_handler.add_mode_change_listener(self.button_controller.sync_mode)
        initialization_progress_bar.advance(10)

        # Initialize CaptureManager
        self.capture_manager = CaptureManager(
            camera_controller=self.camera_controller,
            display_controller=self.display_controller,
            input_handler=self.input_handler,
            pan_servo=self.pan_servo,
            pressure_sensor=self.pressure_sensor,
            remote_api=self.remote_api,
            remote_server=self.remote_server,
            settings=self.settings,
            tilt_servo=self.tilt_servo,
        )

        # Initialize Application Modes
        self.mode_manager = ModeManager(
            input_handler=self.input_handler,
            remote_api=self.remote_api
        )

        base_mode_context = {
            "input_handler": self.input_handler,
            "button_controller": self.button_controller
        }

        app_exit_context = {
            "app_exit_callback": self.exit,
            "app_reboot_callback": self.reboot,
            "app_shutdown_callback": self.shutdown,
        }

        self.menu_mode = MenuMode(
            **base_mode_context,
            **app_exit_context,
            camera_preview=self.preview,
            display_controller=self.display_controller,
            menu=self.menu,
            pressure_sensor=self.pressure_sensor,
            remote_api=self.remote_api
        )

        self.capture_mode = CaptureMode(
            **base_mode_context,
            capture_manager=self.capture_manager
        )

        self.baseline_altitude_mode = BaselineAltitudeMode(
            **base_mode_context,
            display_controller=self.display_controller,
            pressure_sensor_controller=self.pressure_sensor
        )

        self.system_info_mode = SystemInfoMode(
            **base_mode_context,
            **app_exit_context,
            display_controller=self.display_controller,
        )

        self.menu_mode.initialize_inputs()
        self.capture_mode.initialize_inputs()
        self.system_info_mode.initialize_inputs()

        self.mode_manager.register_mode(self.menu_mode)
        self.mode_manager.register_mode(self.capture_mode)
        self.mode_manager.register_mode(self.baseline_altitude_mode)
        self.mode_manager.register_mode(self.system_info_mode)

        # Run Preloader Animation
        preloader = PreLoader(self.display_controller)
        preloader.play()

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

    async def main_loop(self):
        self.application_running = True
        try:
            await self.mode_manager.switch_to(PiKiteMode.MENU)

            while self.application_running:
                await self.mode_manager.run_current_mode()
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
        logger.info("Exit command received. Closing PiKite application.")
        self.application_running = False
        self.mode_manager.request_exit()

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
        
        async def _cleanup_servos():
            # Home the Servos
            self.pan_servo.home()
            await asyncio.sleep(0.1)
            self.tilt_servo.home()
            await asyncio.sleep(0.1)

            # Stop the Servos
            self.pan_servo.stop()
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

        visible_tasks = len(cleanup_tasks) - 1 # Subtract one from cleanup_tasks to account for shutting down the display controller.

        # Call Each Cleanup Task
        for i, task in enumerate(cleanup_tasks):
            try:
                result = task()

                if isawaitable(result):
                    await result
            except Exception as e:
                logger.error(f"Failed to execute cleanup task {task.__name__ if hasattr(task, '__name__') else task}: {e}")
            finally:
                if i == visible_tasks: # visible_tasks equals the index of the final task
                    break # skip since DisplayController has been closed and cannot be updated.
                
                # Advance the progress bar
                if cleanup_progress_bar is not None:
                    completed_tasks = i + 1

                    target_progress = round((completed_tasks / visible_tasks) * 100)
                    advance_amount = target_progress - cleanup_progress_bar.value

                    cleanup_progress_bar.advance(advance_amount)

        logger.info("PiKite clean-up complete. Closing application.")