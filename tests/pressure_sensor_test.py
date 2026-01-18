import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.hardware.pressure_sensor_controller import PressureSensorController

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting Pressure Sensor Tests")

def test_pressure_sensor_initialization():
    pressure_sensor = PressureSensorController()
    assert pressure_sensor is not None
    logger.info("PressureSensorController initialized successfully")