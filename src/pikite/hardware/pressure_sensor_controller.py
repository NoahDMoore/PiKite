import time
import board            # type: ignore
import digitalio        # type: ignore
from busio import I2C   # type: ignore
import adafruit_bmp280  # type: ignore

from ..core.logger import get_logger
from ..core.constants import DISTANCE_UNITS
from .display_controller import LoadingBar

# Setup Logger
logger = get_logger(__name__)

UNIT_CONVERSION = {
    DISTANCE_UNITS.FEET: 3.28084,
    DISTANCE_UNITS.YARDS: 1.09361,
    DISTANCE_UNITS.MILES: 0.000621371,
    DISTANCE_UNITS.METERS: 1.0,
    DISTANCE_UNITS.KILOMETERS: 0.001,
    DISTANCE_UNITS.CENTIMETERS: 100.0,
    DISTANCE_UNITS.MILLIMETERS: 1000.0
}

class PressureSensorController:
    """Controller for the BMP280 Pressure Sensor to measure altitude."""

    def __init__(self):
        """Initialize the PressureSensorController and BMP280 sensor."""
        self.i2c = I2C(board.SCL, board.SDA)
        self.sensor = adafruit_bmp280.Adafruit_BMP280_SPI(board.SPI(), digitalio.DigitalInOut(board.CE1))
        self.sensor.overscan_pressure = adafruit_bmp280.OVERSCAN_X16    # Set overscan for better pressure accuracy

        # Set the initial baseline pressure
        self.baseline_pressure = 1030.0  # Can be adjusted to a localised baseline by calling set_baseline_pressure()

    def get_altitude(self, unit=DISTANCE_UNITS.METERS):
        """
        Calculate the current altitude based on the baseline pressure.
        
        Args:
            unit (DISTANCE_UNITS): The unit for altitude measurement. Default is DISTANCE_UNITS.FEET.

        Returns:
            float: The calculated altitude in the specified unit.
        """
        self.sensor.sea_level_pressure = self.baseline_pressure
        altitude = self.sensor.altitude
        
        altitude *= UNIT_CONVERSION.get(unit, UNIT_CONVERSION[DISTANCE_UNITS.METERS]) # Convert to desired unit, default to meters if unit not found

        return round(altitude, 2)

    @property
    def altitude(self, unit=DISTANCE_UNITS.METERS):
        """
        Get the current altitude as a string.
        
        Returns:
            str: The current altitude.
        """
        # Returns the current altitude as a string.
        return str(self.get_altitude(unit=unit))

    def get_baseline_pressure(self, num_samples=80, display_controller=None):
        """
        Get the baseline pressure by averaging multiple samples.

        Args:
            num_samples (int): The number of pressure samples to average. Default is 80.
            display_controller (DisplayController, optional): An instance of DisplayController to show a loading bar.
        """
        baseline_pressure = 0
        loader = LoadingBar("Baseline Alt:", display_controller) if display_controller is not None else None

        for i in range(num_samples):
            baseline_pressure += self.sensor.pressure
            time.sleep(.1)
            
            if loader is None:
                continue

            if num_samples >= 20:
                divisor = num_samples // 20
                if i % divisor == 0:
                    loader.advance()
            else:
                multiplier = 20 // num_samples
                for i in range(multiplier):
                    loader.advance()

        self.baseline_pressure = baseline_pressure / num_samples