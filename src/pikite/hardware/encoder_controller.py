import smbus    # type: ignore
import math
import time

class EncoderController:
    """Controller for the AS5600 Magnetic Rotary Encoder to measure angle."""
    DEVICE_AS5600 = 0x36 # Default device I2C address

    def __init__(self, bus_number=1):
        """Initialize the EncoderController and AS5600 sensor."""
        self.bus = smbus.SMBus(bus_number)

        self.zero()  # Set the initial zero point

    def _read_raw_angle(self): # Read angle (0-360 represented as 0-4096)
        read_bytes = self.bus.read_i2c_block_data(self.DEVICE_AS5600, 0x0C, 2)
        value = (read_bytes[0] << 8) | read_bytes[1]
        return value & 0x0FFF # Mask to 12 bits
    
    @property
    def angle(self):
        """Get the current angle in degrees."""
        return self.get_angle()

    def get_angle(self):
        """Get the current angle."""
        raw_angle = self._read_raw_angle()
        angle = (raw_angle - self._zero_point) % 4096
        return angle * (360.0 / 4096.0)
    
    def get_smoothed_angle(self, num_samples=5):
        """Get a smoothed angle by averaging multiple readings using circular mean."""
        angles = []
        for _ in range(num_samples):
            angles.append(self.get_angle())
            time.sleep(0.002)  # Small delay between samples to allow for sensor update
        
        # Convert to radians
        angles_rad = [math.radians(a) for a in angles]
        sin_sum = sum(math.sin(a) for a in angles_rad)
        cos_sum = sum(math.cos(a) for a in angles_rad)
        avg_angle_rad = math.atan2(sin_sum / num_samples, cos_sum / num_samples)
        avg_angle_deg = math.degrees(avg_angle_rad) % 360

        if abs(avg_angle_deg - 360.0) < 1e-6:
            avg_angle_deg = 0.0
        
        return avg_angle_deg

    def zero(self):
        """Zero the encoder by setting the current angle as the new zero point."""
        raw_angle = self._read_raw_angle()
        self._zero_point = raw_angle
