import time
import board            # type: ignore
import digitalio        # type: ignore
import adafruit_bmp3xx  # type: ignore

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
    """Controller for the BMP388 Pressure Sensor to measure altitude."""

    def __init__(self):
        """Initialize the PressureSensorController and BMP388 sensor."""
        self.sensor = adafruit_bmp3xx.BMP3XX_SPI(board.SPI(), digitalio.DigitalInOut(board.CE1))

        # Configure the sensor for better accuracy
        self.sensor.pressure_oversampling = 8
        self.sensor.temperature_oversampling = 2
        self.sensor.filter_coefficient = 8
        self.sensor.output_data_rate = 25

        # Set the initial baseline pressure
        self.baseline_pressure = 1030.0  # Can be adjusted to a localised baseline by calling set_baseline_pressure()

        # Altitude Smoothing
        self._smoothed_altitude = None
        self._alpha = 0.15

    def get_altitude(self, unit=DISTANCE_UNITS.METERS):
        """
        Calculate the current altitude based on the baseline pressure.
        
        Args:
            unit (DISTANCE_UNITS): The unit for altitude measurement. Default is DISTANCE_UNITS.FEET.

        Returns:
            float: The calculated altitude in the specified unit.
        """
        self.sensor.sea_level_pressure = self.baseline_pressure
        raw_altitude = self.sensor.altitude
        
        if self._smoothed_altitude is None:
            self._smoothed_altitude = raw_altitude
        else:
            self._smoothed_altitude = (
                self._alpha * raw_altitude + (1 - self._alpha) * self._smoothed_altitude
            )

        altitude = self._smoothed_altitude

        altitude *= UNIT_CONVERSION.get(unit, UNIT_CONVERSION[DISTANCE_UNITS.METERS])

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

        # discard initial unstable readings
        for _ in range(5):
            _ = self.sensor.pressure
            time.sleep(0.05)

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