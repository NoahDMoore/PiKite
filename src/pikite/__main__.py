import asyncio

from pikite.core.input_handler import InputHandler, InputCommand
from pikite.core.lcd_menu import Menu
import pikite.core.logger as logger_module
from pikite.core.settings import Settings
from pikite.core.timer import Timer
from pikite.hardware.camera_controller import CameraController
from pikite.hardware.button_controller import ButtonController
from pikite.hardware.display_controller import DisplayController, LoadingBar, PreLoader
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.servo_controller import TiltServo, PanServo
from pikite.remote.microdot_server import ControllerServer
from pikite.system.storage import StorageManager
import pikite.system.power_management as PowerManagement

# Setup Logger
logger = logger_module.get_logger(__name__)

def configure_logger(settings: Settings):
    """
    Configure the logger based on application settings.

    Args:
        settings (Settings): Application settings.
    """
    log_level = settings.get("log_level", "INFO")
    logger_module.set_log_level(log_level)
    logger.info(f"Log level set to {log_level}")

    if settings.get("log_to_file", True) is False:
        logger.info("Logging to file disabled via settings.")
        logger_module.unset_file_handler()
    
    if settings.get("log_to_console", True) is False:
        logger.info("Logging to console disabled via settings.")
        logger_module.unset_stream_handler()

def initialize_button_input(input_handler: InputHandler) -> ButtonController:
    """
    Initialize the ButtonController for GPIO input handling.

    Args:
        input_handler (InputHandler): The input handler instance.

    Returns:
        ButtonController: The initialized button controller instance.
    """
    button_controller = ButtonController(input_handler)
    
    button_controller.set_commands(
        next_command=InputCommand.NEXT,
        select_command=InputCommand.SELECT,
        scope="MENU"
    )
    
    button_controller.set_commands(
        next_command=InputCommand.STOP_CAPTURE,
        select_command=InputCommand.STOP_CAPTURE,
        scope="RUNNING"
    )

    return button_controller

def initialize_menu(settings: Settings, display_controller: DisplayController, input_handler: InputHandler):
    """
    Initialize the menu system and register input commands.

    Args:
        settings (Settings): Application settings.
        display_controller (DisplayController): The display controller instance.
        input_handler (InputHandler): The input handler instance.

    Returns:
        Menu: The initialized menu instance.
    """
    menu = Menu(display_controller, settings)

    input_handler.set_scope("MENU")

    input_handler.register(
        scope="MENU",
        command=InputCommand.NEXT,
        callback=menu.increment_element
    )

    input_handler.register(
        scope="MENU",
        command=InputCommand.SELECT,
        callback=menu.do_action
    )

    input_handler.register(
        scope="MENU",
        command=InputCommand.SHUTDOWN,
        callback=PowerManagement.shutdown
    )

    input_handler.register(
        scope="MENU",
        command=InputCommand.REBOOT,
        callback=PowerManagement.reboot
    )

    return menu

def capture_loop():
    """
    Main capture loop for handling image capture and processing.
    """
    # Placeholder for capture logic
    pass

async def main():
    logger.info("Starting PiKite Application")

    # Initialize Hardware Controllers
    display_controller = DisplayController()
    initialization_progress_bar = LoadingBar("Loading PiKite", display_controller)
    initialization_progress_bar.advance(10)
    
    # Initialize Timer
    timer = Timer()
    initialization_progress_bar.advance(10)

    # Load Settings
    settings = Settings()
    initialization_progress_bar.advance(10)

    # Configure Logger from Settings
    configure_logger(settings)
    initialization_progress_bar.advance(10)

    # Initialize Sensors
    pressure_sensor = PressureSensorController()
    initialization_progress_bar.advance(5)

    camera_controller = CameraController(settings)
    initialization_progress_bar.advance(5)

    # Initialize Servo Controllers
    tilt_servo = TiltServo()
    initialization_progress_bar.advance(5)

    pan_servo = PanServo(rotation_time = settings.get("pan_rotation_time", 1))  # Default to assuming 1 second for full rotation at full speed
    initialization_progress_bar.advance(5)

    # Initialize Input Handler
    input_handler = InputHandler()
    initialization_progress_bar.advance(10)

    # Initialize Remote Controller Server
    remote_server = ControllerServer(port=5000)
    initialization_progress_bar.advance(10)

    # Initialize Buttons
    button_controller = initialize_button_input(input_handler)
    initialization_progress_bar.advance(10)

    # Run Preloader Animation
    preloader = PreLoader(display_controller)
    preloader.play()

    # Initialize Menu System
    menu = initialize_menu(settings, display_controller, input_handler)

    logger.info("PiKite Application Initialized")

    # Main Application Loop
    application_running = True
    while application_running:
        await asyncio.sleep(0.1)
        if input_handler._active_scope == "MENU":
            pass
        elif input_handler._active_scope == "RUNNING":
            capture_loop()

    # Cleanup at End of Runtime
    button_controller.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.error("Keyboard Interrupt: Exiting PiKite")
        pass