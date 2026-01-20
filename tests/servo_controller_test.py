import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.hardware.servo_controller import TiltServo, PanServo

import time

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting Servo Controller Tests")

# Tilt Servo Tests
def test_tilt_servo_initialization():
    tilt_servo = TiltServo()
    assert tilt_servo is not None
    logger.info("TiltServo initialized successfully")

def test_tilt_servo_move_to_position():
    tilt_servo = TiltServo()

    tilt_servo.angle = 0  # Start at 0 degrees
    logger.info("TiltServo moved to 0 degrees successfully")
    time.sleep(2)
    tilt_servo.angle = 45  # Move to 45 degrees
    logger.info("TiltServo moved to 45 degrees successfully")
    time.sleep(2)
    tilt_servo.angle = 90  # Move to 90 degrees
    logger.info("TiltServo moved to 90 degrees successfully")
    time.sleep(2)
    tilt_servo.angle = 135  # Move to 135 degrees
    logger.info("TiltServo moved to 135 degrees successfully")
    time.sleep(2)
    tilt_servo.angle = 180  # Move to 180 degrees
    logger.info("TiltServo moved to 180 degrees successfully")
    time.sleep(2)