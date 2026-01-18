import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.core.constants import DISTANCE_UNITS
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.display_controller import DisplayController

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting Pressure Sensor Tests")

def test_pressure_sensor_initialization():
    pressure_sensor = PressureSensorController()
    assert pressure_sensor is not None
    logger.info("PressureSensorController initialized successfully")

def test_get_altitude():
    pressure_sensor = PressureSensorController()
    altitude_feet = pressure_sensor.get_altitude(unit=DISTANCE_UNITS.FEET)
    altitude_meters = pressure_sensor.get_altitude(unit=DISTANCE_UNITS.METERS)

    assert isinstance(altitude_feet, float)
    assert isinstance(altitude_meters, float)
    logger.info(f"Test returned Altitude in feet: {altitude_feet}, Altitude in meters: {altitude_meters}")

def test_altitude_property():
    pressure_sensor = PressureSensorController()
    altitude_str = pressure_sensor.altitude
    assert isinstance(altitude_str, str)
    logger.info(f"Test returned Altitude string: {altitude_str}")

def test_get_baseline_pressure_without_loading_bar():
    pressure_sensor = PressureSensorController()
    baseline_pressure = pressure_sensor.get_baseline_pressure(num_samples=10)
    assert isinstance(baseline_pressure, float)
    logger.info(f"Test returned Baseline Pressure: {baseline_pressure}")

def test_get_baseline_pressure_with_loading_bar():
    display_controller = DisplayController()
    pressure_sensor = PressureSensorController()
    baseline_pressure = pressure_sensor.get_baseline_pressure(num_samples=10, display_controller=display_controller)
    assert isinstance(baseline_pressure, float)
    logger.info(f"Test returned Baseline Pressure: {baseline_pressure}")