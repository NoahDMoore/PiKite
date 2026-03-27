import smbus    # type: ignore

DEVICE_AS5600 = 0x36 # Default device I2C address
bus = smbus.SMBus(1)

class EncoderController:
    """Controller for the AS5600 Magnetic Rotary Encoder to measure angle."""

    def __init__(self):
        """Initialize the EncoderController and AS5600 sensor."""
        self.zero()  # Set the initial zero point

    def get_angle(self):
        """Get the current angle."""
        self._raw_angle = read_raw_angle()
        self.angle = (self._raw_angle - self._zero_point) % 4096
        return self.angle * (360.0 / 4096.0)
    
    def zero(self):
        """Zero the encoder by setting the current angle as the new zero point."""
        self._raw_angle = read_raw_angle()
        self._zero_point = self._raw_angle
        self.angle = 0.0

def read_raw_angle(): # Read angle (0-360 represented as 0-4096)
    read_bytes = bus.read_i2c_block_data(DEVICE_AS5600, 0x0C, 2)
    return (read_bytes[0]<<8) | read_bytes[1];