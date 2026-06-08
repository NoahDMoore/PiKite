from pikite.hardware.servos.initialize_pwm import initialize_pwm
from pikite.utils.logger import get_logger

# Setup Logger
logger = get_logger(__name__)

class TiltServo:
    """
    Class to control a traditional servo motor for tilt movements of a camera.

    This class allows for controlling a traditional servo motor using PWM signals to set the angle of the servo.
    It supports setting the angle in degrees, where 0 degrees is the minimum position and a specified maximum angle is the maximum position.
    """
    def __init__(self, pwm_channel=0, frequency=50, chip=0, max_angle=180, min_pulse_width=500, max_pulse_width=2500, tilt_zero_position_offset: int = 0):
        """
        Initializes the TiltServo with the specified parameters.

        Args:
            pwm_channel (int): The PWM channel to use (0 or 1). Channel 0 uses GPIO 18/12, and Channel 1 uses GPIO 19/13.
            frequency (int): The PWM frequency in Hz, default is 50Hz.
            chip (int): The chip number for the PWM channel, default is 0.
                    As of linux kernel 6.12, chip=0 is used for all Raspberry Pi models.
            max_angle (int): Maximum angle in degrees for the servo, default is 180 degrees.
            min_pulse_width (int): Minimum pulse width in microseconds for the servo at 0 degrees, default is 500us (based on FS08MD servo).
            max_pulse_width (int): Maximum pulse width in microseconds for the servo at max_angle degrees, default is 2500us (based on FS08MD servo).
        """

        # Initialize PWM channel, frequency, and chip
        if pwm_channel in [0, 1]:
            self.pwm_channel = pwm_channel
        else:
            try:
                raise ValueError("Invalid PWM channel. Use 0 or 1.")
            except ValueError as e:
                logger.critical(f"Value Error: {e}.")
                raise
        self.frequency = frequency
        self.chip = chip

        # Initialize the PWM with the specified channel, frequency, and chip
        self.pwm = initialize_pwm(
            pwm_channel=self.pwm_channel,
            frequency=self.frequency,
            chip=self.chip,
            retries=2
        )

        # Calculate the PWM period in microseconds based on the frequency
        self.period = (1 / self.frequency) * 1000000    # PWM Period in microseconds

        # Set the maximum angle and pulse widths for the servo
        self.max_angle = max_angle
        self.min_pulse_width = min_pulse_width
        self.max_pulse_width = max_pulse_width

        # Apply zero angle offset to angle calculations
        if not isinstance(tilt_zero_position_offset, int):
            try:
                raise ValueError("Zero angle offset must be an integer.")
            except ValueError as e:
                logger.error(f"Value Error: {e}. Defaulting zero angle offset to 0.")
                tilt_zero_position_offset = 0
        self.tilt_zero_position_offset = tilt_zero_position_offset

        # Calculate the pulse width per degree
        self.pulse_width_per_degree = (self.max_pulse_width - self.min_pulse_width) / self.max_angle

        # Start the servo motor in the 0 degree position
        self.angle = 0    # Start the servo motor at 0 degrees

    def __repr__(self):
        return f"TiltServo(pwm_channel={self.pwm_channel}, frequency={self.frequency}, chip={self.chip})"

    def __str__(self):
        return f"TiltServo on PWM channel {self.pwm_channel} with frequency: {self.frequency}Hz, chip: {self.chip}"

    def __del__(self):
        """Ensure the PWM is stopped when the object is deleted."""
        self.stop()

    @property
    def angle(self) -> int:
        """
        Returns the current angle of the servo motor.

        Returns:
            int: Current angle in degrees.
        """
        return self._angle - self.tilt_zero_position_offset

    @angle.setter
    def angle(self, angle: int = 0) -> None:
        """
        Start the servo motor at a given angle; defaults to 0 degrees.

        Args:
            angle (int): Angle in degrees to position the servo, where 0 is the minimum angle and self.max_angle is the maximum angle.

        Raises:
            ValueError: If angle is not between 0 and max_angle.
        """
        angle += self.tilt_zero_position_offset  # Apply zero angle offset to the input angle

        if 0 <= angle <= self.max_angle:
            pulse_width = self.min_pulse_width + (angle * self.pulse_width_per_degree)
            duty_cycle = (pulse_width / self.period) * 100
            self.pwm.start(duty_cycle)
            self._angle = angle  # Update the current angle
        else:
            try:
                raise ValueError(f"Angle must be between 0 and {self.max_angle} degrees.")
            except ValueError as e:
                logger.error(f"Value Error: {e}. No change made to servo angle.")

    @angle.deleter
    def angle(self) -> None:
        """Deletes the current angle setting and stops the servo motor."""
        del self._angle
        self.stop()

    def set_angle(self, angle: int, **kwargs) -> None:
        """
        Set the servo motor to a specific angle.

        Args:
            angle (int): Angle in degrees to position the servo, where 0 is the minimum angle and self.max_angle is the maximum angle.

        Raises:
            ValueError: If angle is not between 0 and max_angle.
        """
        self.angle = angle  # Use the angle property setter to set the angle

    def stop(self) -> None:
        """Stops the servo motor by setting the duty cycle to 0%."""
        self.pwm.stop()

    def home(self) -> None:
        """Returns the servo to 0 degrees."""
        self.angle = 0