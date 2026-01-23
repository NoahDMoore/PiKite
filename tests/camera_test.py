import sys
from pathlib import Path

from pikite.hardware import camera_controller

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.core.settings import Settings
from pikite.core.constants import CAPTURE_MODES, MEDIA_EXTENSIONS
from pikite.hardware.camera_controller import CameraController
from pikite.system.storage import StorageManager

import time

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting CameraController Tests")

def test_camera_controller_class_initialization():
    settings = Settings()
    with CameraController(settings) as camera_controller:
        assert isinstance(camera_controller, CameraController)
    logger.info("CameraController initialization test passed.")

def test_capture_image():
    settings = Settings()
    storage_manager = StorageManager()
    session_dir = storage_manager.new_session_dir(CAPTURE_MODES.STILL)

    with CameraController(settings) as camera_controller:
        image_path = storage_manager.media_file_path(
            mode=CAPTURE_MODES.STILL,
            extension=MEDIA_EXTENSIONS.JPG,
            use_timestamp=True,
            session_dir=session_dir
        )

        camera_controller.capture_image(image_path)
        time.sleep(2)  # Wait for the image to be saved
        assert image_path.exists()
        assert image_path.stat().st_size > 0
    logger.info(f"Image capture test passed. Image saved at {image_path}")