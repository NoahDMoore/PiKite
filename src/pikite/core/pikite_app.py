import asyncio
from typing import Callable
from inspect import isawaitable

from pikite.core.capture.capture_manager import CaptureManager
from pikite.core.input_handler import InputHandler
from pikite.core.menu import Menu
from pikite.core.modes.baseline_altitude_mode import BaselineAltitudeMode
from pikite.core.modes.capture_mode import CaptureMode
from pikite.core.modes.menu_mode import MenuMode
from pikite.core.modes.mode_manager import ModeManager
from pikite.core.modes.pikite_mode import PiKiteMode
from pikite.core.modes.system_info_mode import SystemInfoMode
from pikite.core.settings import Settings
from pikite.hardware.button_controller import ButtonController
from pikite.hardware.camera.camera_controller import CameraController
from pikite.hardware.camera.preview_stream import PreviewStream
from pikite.hardware.display.display_controller import DisplayController
from pikite.hardware.display.loading_bar import LoadingBar
from pikite.hardware.display.pre_loader import PreLoader
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.servos.pan_servo import PanServo
from pikite.hardware.servos.tilt_servo import TiltServo
from pikite.remote.remote_api import RemoteAPI
from pikite.remote.remote_input_listener import RemoteInputListener
from pikite.remote.remote_server import RemoteServer
from pikite.system.storage import StorageManager
import pikite.system.power_management as PowerManagement
import pikite.utils.logger as logger_module
import pikite.utils.lifecyle_task_sequencer as lifecycle_module
from pikite.utils.timer import Timer

# Setup Logger
logger = logger_module.get_logger(__name__)

class PiKiteApp:
    def __init__(self):
        self.application_running = False
        self.initialized = False
        self.on_close_callback: Callable[[], None] | None = None

    @classmethod
    async def create(cls):
        self = cls()
        await self._bootstrap()
        self.initialized = True
        logger.info("PiKite Application Initialized")
        return self

    async def _bootstrap(self):
        self.lifecycle_steps: list[lifecycle_module.LifecycleStep] = [
            lifecycle_module.LifecycleStep(
                name = "display",
                startup = None, # Display must be intialized as a pre-requisite before calling lifecycle_module.startup()
                shutdown = self._cleanup_display,
                weight = 1
            ),
            lifecycle_module.LifecycleStep(
                name = "utils",
                startup = self._init_settings_and_utils,
                shutdown = self._cleanup_app_timer,
                weight = 1
            ),
            lifecycle_module.LifecycleStep(
                name = "hardware",
                startup = self._init_hardware,
                shutdown = self._cleanup_servos,
                weight = 1
            ),
            lifecycle_module.LifecycleStep(
                name = "input",
                startup = self._init_inputs,
                shutdown = self._cleanup_inputs,
                weight = 1
            ),
            lifecycle_module.LifecycleStep(
                name = "remote",
                startup = self._init_remote_system,
                shutdown = self._cleanup_remote_system,
                weight = 1
            ),
            lifecycle_module.LifecycleStep(
                name = "capture",
                startup = self._init_capture_system,
                shutdown = self._cleanup_capture_system,
                weight = 1
            ),
            lifecycle_module.LifecycleStep(
                name = "modes",
                startup = self._init_modes,
                shutdown = None,
                weight = 1
            ),
        ]

        # Initialize DisplayController as a Pre-Requsite
        self._init_display()

        await lifecycle_module.startup(
            lifecycle_steps = self.lifecycle_steps,
            progress_bar = LoadingBar("Loading PiKite", self.display_controller),
            parent_logger = logger,
        )

    def _init_display(self):
        self.display_controller = DisplayController()

    def _cleanup_display(self):
        self.display_controller.put(
            payload="PiKite Closed",
            bg_color=(0,0,0),
            fg_color=(255,255,255)
        )

        # Cleanup Display Controller
        self.display_controller.close()

    def _init_settings_and_utils(self):
        self.timer = Timer()
        self.storage_manager = StorageManager()
        self.settings = Settings()
        self.settings.add_change_listener(self._on_setting_change)
        self.configure_logger()

    def _cleanup_app_timer(self):
        runtime = self.timer.stop()
        logger.info(f"PiKite has run for {self.timer.format_elapsed_time(runtime)}.")

    def _on_setting_change(self, setting_key, new_value):
        logger.info(f"Setting Change Detected: {setting_key} changed to {new_value}.")
        
        if setting_key.startswith("logging"):
            self.configure_logger()
            logger.info("Logger reconfigured due to logging settings change.")

        if setting_key.startswith("camera"):
            self.camera_controller.reconfigure_camera()
            self.timer.wait(0.5) # Small delay to allow camera to reconfigure before use
            logger.info("Camera controller reconfigured due to camera settings change.")

        if setting_key == "pan_tilt.tilt_zero_position_offset":
            self.tilt_servo.tilt_zero_position_offset = int(new_value)
            self.tilt_servo.home()
            logger.info(f"Updated tilt servo zero angle offset to {new_value} due to settings change.")

    def configure_logger(self):
        """
        Configure the logger based on application settings.

        Args:
            settings (Settings): Application settings.
        """
        log_level = self.settings.get("logging.log_level", "INFO")
        log_to_console = self.settings.get("logging.log_to_console", True)
        log_to_file = self.settings.get("logging.log_to_file", True)
        
        logger_module.configure_logger(
            log_level = log_level,
            use_console_handler = log_to_console,
            use_file_handler = log_to_file,
            log_file = self.storage_manager.LOG_FILE_BASE
        )

    def _init_hardware(self):
        # Initialize Sensors
        self.pressure_sensor = PressureSensorController()

        # Initialize Servos
        offset = int(self.settings.get("pan_tilt.tilt_zero_position_offset", 0))
        self.tilt_servo = TiltServo(tilt_zero_position_offset=offset) # Adjust zero angle offset to ensure camera is level when tilt angle is set to 0
        self.pan_servo = PanServo()

    async def _cleanup_servos(self):
        # Home the Servos
        self.pan_servo.home()
        await asyncio.sleep(0.1)
        self.tilt_servo.home()
        await asyncio.sleep(0.1)

        # Stop the Servos
        self.pan_servo.stop()
        self.tilt_servo.stop()

    def _init_inputs(self):
        # Initialize InputHandler
        self.input_handler = InputHandler()

        # Initialize Buttons
        self.button_controller = ButtonController(self.input_handler)
        self.input_handler.add_mode_change_listener(self.button_controller.sync_mode)
        
        # Initialize Menu
        self.menu = Menu(self.display_controller, self.settings, self.input_handler) #type: ignore

    def _cleanup_inputs(self):
        self.button_controller.close()

    def _init_remote_system(self):
        # Initialize Remote Controller Server
        self.remote_server = RemoteServer(port=5000)
        
        # Initialize Remote Input Handler
        self.remote_input_listener = RemoteInputListener(self.remote_server, self.input_handler)
        
        # Initialize RemoteAPI and attach it to the server
        self.remote_api = RemoteAPI(
            pan_servo=self.pan_servo,
            remote_server=self.remote_server,
            settings=self.settings,
            storage_manager=self.storage_manager,
            tilt_servo=self.tilt_servo
        )
        self.remote_server.register_api(self.remote_api)

    async def _cleanup_remote_system(self):
        self.remote_input_listener.close()
        await self.remote_server.close()

    def _init_capture_system(self):
        # Initialize Camera
        self.camera_controller = CameraController(self.settings)

        # Initialize Camera Preview Stream
        self.preview = PreviewStream(self.camera_controller, self.remote_server)

        # Initialize CaptureManager
        self.capture_manager = CaptureManager(
            camera_controller=self.camera_controller,
            display_controller=self.display_controller,
            pan_servo=self.pan_servo,
            pressure_sensor=self.pressure_sensor,
            remote_api=self.remote_api,
            settings=self.settings,
            tilt_servo=self.tilt_servo,
        )

    async def _cleanup_capture_system(self):
        await self.preview.close()
        self.camera_controller.close()

    def _init_modes(self):
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
            capture_manager=self.capture_manager,
            remote_api=self.remote_api
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

    # On Close Methods
    def register_on_close_callback(self, callback: Callable[[], None]):
        self.on_close_callback = callback

    def on_close(self):
        if callable(self.on_close_callback):
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

    # Main Loop
    async def main_loop(self):
        # Run Preloader Animation
        preloader = PreLoader(self.display_controller)
        await preloader.run()

        self.application_running = True

        await self.mode_manager.switch_to(PiKiteMode.MENU)

        while self.application_running:
            await self.mode_manager.run_current_mode()

        logger.info("EXITING")

    async def run(self):
        logger.info("Starting PiKite Application")

        self.timer.start()

        self.remote_server.start()

        remote_task = asyncio.create_task(
            self.remote_input_listener.start_listening()
        )

        preview_task = asyncio.create_task(
            self.preview.stream()
        )

        try:
            await self.main_loop()
        finally:
            await self.cleanup()

            await remote_task
            await preview_task

            self.on_close()

    async def cleanup(self):
        # Cleanup at End of Runtime
        logger.info("Preparing to close PiKite. Cleaning up...")

        await lifecycle_module.shutdown(
            lifecycle_steps = self.lifecycle_steps,
            progress_bar = LoadingBar("Closing PiKite", self.display_controller),
            use_dynamic_progress_bar_titles = True,
            hide_last_update = True,
            parent_logger = logger
        )
    
        logger.info("PiKite clean-up complete. Closing application.")