import asyncio

from pikite.core.constants import CAPTURE_MODES
from pikite.core.input_handler import InputHandler
from pikite.core.lcd_menu import Menu
from pikite.core.logger import get_logger
from pikite.core.settings import Settings
from pikite.core.timer import Timer
from pikite.hardware.camera_controller import CameraController
from pikite.hardware.display_controller import DisplayController
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.servo_controller import TiltServo, PanServo
from pikite.remote.microdot_server import ControllerServer
from pikite.system.storage import StorageManager

# Setup Logger
logger = get_logger(__name__)

async def main():
    logger.info("Starting PiKite Application")
    
    # Initialize Storage Manager
    storage_manager = StorageManager()
    PHOTO_OUTPUT_DIR = storage_manager.PHOTO_OUTPUT_DIR
    VIDEO_OUTPUT_DIR = storage_manager.VIDEO_OUTPUT_DIR

    settings = Settings()
    display_controller = DisplayController()
    pressure_sensor = PressureSensorController()
    camera_controller = CameraController(settings)
    tilt_servo = TiltServo()
    pan_servo = PanServo(rotation_time = settings.get("pan_rotation_time", 1))  # Default to assuming 1 second for full rotation at full speed
    
    logger.info("PiKite Application Initialized")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.error("Keyboard Interrupt: Exiting PiKite")
        pass