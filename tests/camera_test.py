import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.core.settings import Settings
from pikite.hardware.camera_controller import CameraController

import time

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting CameraController Tests")

def test_camera_controller_class_initialization():
    settings = Settings()
    camera_controller = CameraController(settings)
    assert camera_controller is not None
    logger.info("CameraController initialization test passed.")