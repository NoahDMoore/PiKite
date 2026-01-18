import time
import board            # type: ignore
import digitalio        # type: ignore
from busio import I2C   # type: ignore
import adafruit_bmp280  # type: ignore

from ..core.logger import get_logger
from .display_controller import LoadingBar

# Setup Logger
logger = get_logger(__name__)

class PressureSensorController:
    """Controller for the BMP280 Pressure Sensor to measure altitude."""
    def __init__(self):
        """Initialize the PressureSensorController and BMP280 sensor."""
        self.i2c = I2C(board.SCL, board.SDA)
        self.sensor = adafruit_bmp280.Adafruit_BMP280_SPI(board.SPI(), digitalio.DigitalInOut(board.CE1))
        self.sensor.overscan_pressure = adafruit_bmp280.OVERSCAN_X16    # Set overscan for better pressure accuracy

        # Set the initial baseline pressure
        self.baseline_pressure = 1030.0  # Can be adjusted to localised baseline by calling set_baseline_pressure()
    
    def get_altitude(self, unit="feet"):
        self.sensor.sea_level_pressure = self.baseline_pressure
        altitude = self.sensor.altitude

        # Convert altitude to US Feet by default (sensor returns in meters)
        if unit == "feet":
            altitude *= 3.28084

        return round(altitude, 2)

    @property
    def altitude(self):
        # Returns the current altitude as a string.
        return str(self.get_altitude())

    def set_baseline_pressure(self, num_samples=80, display_controller=None):
        baseline_pressure = 0
        loader = LoadingBar("Baseline Alt:", display_controller) if display_controller is not None else None
        for i in range(num_samples):
            baseline_pressure += self.sensor.pressure
            time.sleep(.1)
            
            divisor = num_samples // 20
            if i % divisor == 0 and loader is not None:
                loader.advance()

        self.baseline_pressure = baseline_pressure / num_samples