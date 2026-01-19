import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.hardware.servo_controller import TiltServo, PanServo

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting Servo Controller Tests")

# Tilt Servo Tests
def test_tilt_servo_initialization():
    tilt_servo = TiltServo()
    assert tilt_servo is not None
    logger.info("TiltServo initialized successfully")