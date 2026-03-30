import smbus    # type: ignore

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
    
    def zero(self):
        """Zero the encoder by setting the current angle as the new zero point."""
        raw_angle = self._read_raw_angle()
        self._zero_point = raw_angle
