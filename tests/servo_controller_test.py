import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.core.timer import Timer
from pikite.hardware.servo_controller import TiltServo, PanServo, PanTiltPattern, DIRECTION

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

# Pan Servo Tests
def test_pan_servo_initialization():
    pan_servo = PanServo()
    assert pan_servo is not None
    logger.info("PanServo initialized successfully")

def test_pan_servo_rotate():
    pan_servo = PanServo()

    pan_servo.start(direction=DIRECTION.CW)
    logger.info("PanServo rotating clockwise")
    time.sleep(3)  # Rotate for 3 seconds
    pan_servo.stop()
    logger.info("PanServo stopped successfully")
    time.sleep(2)

    pan_servo.start(direction=DIRECTION.CCW)
    logger.info("PanServo rotating counterclockwise")
    time.sleep(3)  # Rotate for 3 seconds
    pan_servo.stop()
    logger.info("PanServo stopped successfully")

def test_pan_tilt_pattern(pattern):
    pan_servo = PanServo()
    assert pan_servo is not None
    logger.info("PanServo initialized successfully")
                
    tilt_servo = TiltServo()
    assert tilt_servo is not None
    logger.info("TiltServo initialized successfully")

    mode = PanTiltPattern.PAN_TILT_MODES[pattern]

    timer = Timer()
    timer.start()
    pan_tilt_pattern = PanTiltPattern(mode, pan_servo, tilt_servo)

    while timer.elapsed() < 300.0: # type: ignore (to suppress mypy warning; elapsed() cannot return None if the timer is running or paused)
        if timer.interval_elapsed(5, "pattern_test"):
            pan_tilt_pattern.step()