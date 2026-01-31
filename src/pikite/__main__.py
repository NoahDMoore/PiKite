import asyncio
import csv

import pikite.core.constants as CONSTANTS
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
from pikite.system.storage import StorageManager, get_timestamp
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
        scope="CAPTURE"
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
    menu = Menu(display_controller, settings, input_handler)

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
        command=InputCommand.START_CAPTURE,
        callback=lambda: input_handler.set_scope("CAPTURE")
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

def capture_loop(
        timer: Timer,
        settings: Settings,
        storage_manager: StorageManager,
        input_handler: InputHandler,
        pressure_sensor: PressureSensorController,
        display_controller: DisplayController,
        camera_controller: CameraController,
        tilt_servo: TiltServo,
        pan_servo: PanServo
    ):
    """
    Main capture loop for handling image capture and processing.
    """
    timer.mark("capture_loop_start")

    capture_mode = settings.get("capture_mode", CONSTANTS.CAPTURE_MODES.NONE)
    
    if capture_mode == CONSTANTS.CAPTURE_MODES.STILL:
        capture_interval = settings.get("pic_interval", 2)
        media_extension = CONSTANTS.MEDIA_EXTENSIONS.JPG
    elif capture_mode == CONSTANTS.CAPTURE_MODES.VIDEO:
        capture_interval = settings.get("vid_interval", 30)
        media_extension = CONSTANTS.MEDIA_EXTENSIONS.MP4
    else:
        capture_interval = 2  # Default interval for NONE mode
        media_extension = None
        logger.info("Capture mode is NONE; no capture will be performed.")

    video_length = settings.get("vid_length", 15)
    video_repeat = settings.get("vid_multiple", True)

    altitude_interval = settings.get("alt_interval", capture_interval)
    pan_tilt_interval = settings.get("pan_tilt_interval", 30)

    try:
        session_dir = storage_manager.new_session_dir(capture_mode)
    except ValueError as e:
        logger.warning(e)
        session_dir = None

    alt_csv_path = storage_manager.get_data_file_path()

    input_handler.register(
        scope="CAPTURE",
        command=InputCommand.STOP_CAPTURE,
        callback=lambda: input_handler.set_scope("MENU")
    )

    input_handler.register(
        scope="CAPTURE",
        command=InputCommand.PAN,
        callback=pan_servo.rotate
    )

    input_handler.register(
        scope="CAPTURE",
        command=InputCommand.TILT,
        callback=tilt_servo.set_angle
    )

    pressure_sensor.get_baseline_pressure(num_samples=80, display_controller=display_controller)

    display_controller.clear()

    with open(alt_csv_path, "w", newline="") as alt_csv:
        csv_writer = csv.writer(alt_csv)
        csv_writer.writerow(["Timestamp", "Altitude (m)"])

        while input_handler.active_scope == "CAPTURE":
            if timer.interval_elapsed(interval=1.0, name="runtime"):
                display_controller.print_message(f"PiKite Running: | {
                    timer.format_elapsed_time(timer.since_mark('capture_loop_start'))
                }")

            media_path = storage_manager.media_file_path(
                mode=capture_mode, 
                extension=media_extension,
                session_dir=session_dir
            ) if media_extension else None

            if timer.interval_elapsed(interval=capture_interval, name="capture_interval"):
                match capture_mode:
                    case CONSTANTS.CAPTURE_MODES.NONE:
                        pass # Do Nothing if the capture mode is set to None
                    case CONSTANTS.CAPTURE_MODES.STILL:
                            camera_controller.capture_image(media_path)
                    case CONSTANTS.CAPTURE_MODES.VIDEO:
                        if not camera_controller.is_recording:
                            camera_controller.start_video(media_path)
                            timer.set_named_interval("video_length")
                        
            if camera_controller.is_recording and timer.interval_elapsed(interval=video_length, name="video_length"):
                    camera_controller.stop_video()
                    timer.set_named_interval("capture_interval")

            if timer.interval_elapsed(interval=altitude_interval, name="altitude_interval"):
                altitude = pressure_sensor.altitude
                timestamp = get_timestamp()
                csv_writer.writerow([timestamp, altitude])

            if timer.interval_elapsed(interval=pan_tilt_interval, name="pan_tilt") and not camera_controller.is_recording:
                # pan_tilt_pattern.step()
                pass
        
        # Clear Capture Intervals
        del(timer.named_intervals["runtime"])
        del(timer.named_intervals["capture_interval"])
        del(timer.named_intervals["altitude_interval"])

async def main():
    logger.info("Starting PiKite Application")

    # Initialize Display
    display_controller = DisplayController()
    initialization_progress_bar = LoadingBar("Loading PiKite", display_controller)
    initialization_progress_bar.advance(10)
    
    # Initialize Timer
    timer = Timer()
    timer.start()
    initialization_progress_bar.advance(10)

    # Initialize Storage Manager
    storage_manager = StorageManager()
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
        if input_handler.active_scope == "MENU":
            pass
        elif input_handler.active_scope == "CAPTURE":
            capture_loop(
                timer=timer,
                settings=settings,
                storage_manager=storage_manager,
                input_handler=input_handler,
                pressure_sensor=pressure_sensor,
                display_controller=display_controller,
                camera_controller=camera_controller,
                tilt_servo=tilt_servo,
                pan_servo=pan_servo
            )

    # Cleanup at End of Runtime
    button_controller.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.error("Keyboard Interrupt: Exiting PiKite")
        pass