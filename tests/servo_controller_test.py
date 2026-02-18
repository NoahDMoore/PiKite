import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.core.timer import Timer
from pikite.hardware.servo_controller import TiltServo, PanServo, PanTiltPattern, DIRECTION
from pikite.system.storage import StorageManager

import csv
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

# Pan Servo Tests
def test_pan_servo_initialization():
    pan_servo = PanServo()
    assert pan_servo is not None
    logger.info("PanServo initialized successfully")

def test_pan_servo_rotate():
    pan_servo = PanServo()

    pan_servo.start(speed=1.0, direction=DIRECTION.CW)
    logger.info("PanServo rotating clockwise")
    time.sleep(3)  # Rotate for 3 seconds
    pan_servo.stop()
    logger.info("PanServo stopped successfully")
    time.sleep(2)

    pan_servo.start(speed=1.0, direction=DIRECTION.CCW)
    logger.info("PanServo rotating counterclockwise")
    time.sleep(3)  # Rotate for 3 seconds
    pan_servo.stop()
    logger.info("PanServo stopped successfully")

def test_pan_tilt_pattern(pattern, rotation_time):
    pan_servo = PanServo(rotation_time=rotation_time)
    assert pan_servo is not None
    logger.info("PanServo initialized successfully")
                
    tilt_servo = TiltServo()
    assert tilt_servo is not None
    logger.info("TiltServo initialized successfully")

    mode = PanTiltPattern.PAN_TILT_MODES(pattern)

    timer = Timer()
    timer.start()
    pan_tilt_pattern = PanTiltPattern(mode, pan_servo, tilt_servo)

    while timer.elapsed() < 300.0: # type: ignore (to suppress mypy warning; elapsed() cannot return None if the timer is running or paused)
        if timer.interval_elapsed(5, "pattern_test"):
            pan_tilt_pattern.step()

def calibrate_pan_servo_rotation_time(test_duration=5.0):
    SPEEDS = [0.1, 0.2, 0.3, 0.5, 0.7, 1.0]
    TEST_DURATION = test_duration  # Time to rotate at each speed, in seconds

    storage_manager = StorageManager()
    data_output_path = storage_manager.get_data_file_path()

    pan_servo = PanServo()

    logger.info("Servo Calibration: Degrees/sec at Different Speeds")
    logger.info(f"Test duration: {TEST_DURATION} seconds per speed.\n")

    pan_servo.start(speed=0.0, direction=DIRECTION.CW)  # Start at lowest speed for initial setup
    
    results = []
    
    for speed in SPEEDS:
        input(f"Prepare to test speed {speed}. Press Enter to start...")

        pan_servo.change(speed, DIRECTION.CW)
        logger.info(f"Running at speed {speed} for {TEST_DURATION} seconds...")
        time.sleep(TEST_DURATION)
        pan_servo.halt()
        
        deg = input(f"Enter degrees rotated: ")
        try:
            deg = float(deg)
            deg_per_sec = deg / TEST_DURATION
            results.append((speed, deg, deg_per_sec))
            logger.info(f"Speed: {speed}, Degrees: {deg}, Degrees/sec: {deg_per_sec:.2f}\n")
        except ValueError:
            logger.warning("Invalid input, skipping this speed.\n")

    # Save results
    with open(data_output_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["speed", "degrees", "degrees_per_sec"])
        writer.writerows(results)