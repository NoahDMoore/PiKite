from enum import Enum

from pikite.hardware.encoder_controller import EncoderController
from pikite.hardware.servos.initialize_pwm import initialize_pwm
from pikite.utils.logger import get_logger
from pikite.utils.timer import Timer

# Setup Logger
logger = get_logger(__name__)

# Initialize Timer
timer = Timer()

class DIRECTION(Enum):
    CW = "cw"   # Clockwise
    CCW = "ccw" # Counter-clockwise

class PanServo:
    """
    Class to control a continuous rotation servo motor for pan movements of a camera.

    This class allows for controlling a continuous rotation servo motor using PWM signals to set the speed and direction of rotation.
    It supports setting the speed as a float between 0.0 (stopped) and 1.0 (full speed), and the direction as either clockwise (CW) or counter-clockwise (CCW).
    """
    def __init__(self, pwm_channel=1, frequency=50, chip=0, cw_pulse_width=700, ccw_pulse_width=2300, stop_pulse_width=1500):
        """
        Initializes the PanServo with the specified parameters.

        Args:
            pwm_channel (int): The PWM channel to use (0 or 1). Channel 0 uses GPIO 18/12, and Channel 1 uses GPIO 19/13.
            frequency (int): The PWM frequency in Hz, default is 50Hz.
            chip (int): The chip number for the PWM channel, default is 0.
                    As of linux kernel 6.12, chip=0 is used for all Raspberry Pi models.
            cw_pulse_width (int): Pulse width in microseconds for full speed clockwise rotation. Default is based on FS90 continuous rotation servo.
            ccw_pulse_width (int): Pulse width in microseconds for full speed counter-clockwise rotation. Default is based on FS90 continuous rotation servo.

        Raises:
            ValueError: If pwm_channel is not 0 or 1.
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

        # Set microsecond pulse widths for full speed clockwise and counter-clockwise, and calculate the stop position pulse width.
        self.cw_pulse_width = cw_pulse_width
        self.ccw_pulse_width = ccw_pulse_width
        self.stop_pw = stop_pulse_width

        self.stop_duty_cycle = self.get_duty_cycle(0.0, DIRECTION.CW)   # Duty cycle for stop position

        self.encoder = EncoderController() # Initialize the encoder controller to measure angle of rotation

        # Set initial speed and direction
        self.speed = 0.0               # Default speed is 0.0 (stopped)
        self.direction = DIRECTION.CW  # Default direction is clockwise

        # Start the servo motor in the stop position
        self.start(self.speed, self.direction)  # Start the servo motor with initial speed and direction

    def __repr__(self):
        return f"PanServo(pwm_channel={self.pwm_channel}, frequency={self.frequency}, chip={self.chip})"

    def __str__(self):
        return f"PanServo on PWM channel {self.pwm_channel} with frequency: {self.frequency}Hz, chip: {self.chip}"

    def __del__(self):
        """Ensure the PWM is stopped when the object is deleted."""
        self.stop()

    def start(self, speed: float = 0.0, direction: DIRECTION = DIRECTION.CW) -> None:
        """
        Start the servo motor with a given speed and direction; defaults to stop position.

        Args:
            speed (float): Speed of the servo motor, where 0.0 is stopped and 1.0 is full speed
            direction (DIRECTION): Direction of rotation, either DIRECTION.CW or DIRECTION.CCW

        Raises:
            ValueError: If speed is not between 0 and 1
            ValueError: If direction is not DIRECTION.CW or DIRECTION.CCW
        """
        self.direction = direction  # Set the initial direction
        self.speed = speed          # Set the initial speed
        self.pwm.start(self.get_duty_cycle(speed, direction))

    def change(self, speed: float, direction: DIRECTION) -> None:
        """
        Change the speed and direction of the servo motor.

        Args:
            speed (float): Speed of the servo motor, where 0.0 is stopped and 1.0 is full speed
            direction (DIRECTION): Direction of rotation, either DIRECTION.CW or DIRECTION.CCW

        Raises:
            ValueError: If speed is not between 0 and 1
            ValueError: If direction is not DIRECTION.CW or DIRECTION.CCW
        """

        self.direction = direction  # Update the current direction
        self.speed = speed          # Update the current speed
        self.pwm.change_duty_cycle(self.get_duty_cycle(self.speed, self.direction))

    def stop(self) -> None:
        """This method halts the servo motor by stopping the PWM signal, and resets the speed and direction."""
        self.pwm.stop()                 # Stop the PWM signal
        self.speed = 0.0                # Reset the speed to 0
        self.direction = DIRECTION.CW   # Reset the direction to CW

    def home(self) -> None:
        """Returns the servo to 0 degrees."""
        self.rotate_to(speed=0.5, target_angle=0)

    def rotate_by(self, speed: float, direction: DIRECTION, degrees: int, margin: int = 4, **kwargs) -> None:
        """
        Rotate the servo motor an approximate number of degrees at a given speed and direction using proportional control.
        Uses EncoderController to measure the angle of rotation, halting when the desired angle is reached.

        Args:
            speed (float): Maximum speed of the servo motor, where 0.0 is stopped and 1.0 is full speed
            direction (DIRECTION): Direction of rotation, either DIRECTION.CW or DIRECTION.CCW
            degrees (int): Number of degrees to rotate, must be greater than 0; 360 degrees is a full rotation
            margin (int): Margin of error for target angle, in degrees

        Raises:
            ValueError: If degrees is negative
            ValueError: If margin is negative
            ValueError: If speed is not between 0.0 and 1.0
            ValueError: If direction is not DIRECTION.CW or DIRECTION.CCW
        """
        if degrees < 0:
            try:
                raise ValueError("Degrees must be nonnegative")
            except ValueError as e:
                logger.error(f"Value Error: {e}. No rotation will be performed.")
                return

        if margin < 0:
            try:
                raise ValueError("Margin must be nonnegative")
            except ValueError as e:
                logger.error(f"Value Error: {e}. Using default margin of 4 degrees.")
                margin = 4

        starting_angle = self.encoder.get_smoothed_angle()
        target_angle = (starting_angle + degrees) % 360 if direction == DIRECTION.CCW else (starting_angle - degrees) % 360

        logger.debug(f"Rotating from {starting_angle:.2f}° to {target_angle:.2f}° at max speed {speed} in direction {direction.value}.")

        self.proportional_rotate(speed, target_angle, margin)

    def rotate_to(self, target_angle: int, speed: float = 0.5, margin: int = 4) -> None:
        """
        Rotate the servo motor to a specific target angle at a given speed and direction using proportional control.
        Uses EncoderController to measure the angle of rotation, halting when the desired angle is reached.

        Args:
            speed (float): Maximum speed of the servo motor, where 0.0 is stopped and 1.0 is full speed
            target_angle (int): Target angle to rotate to, in degrees from 0 to 360
            margin (int): Margin of error for target angle, in degrees

        Raises:
            ValueError: If target_angle is not between 0 and 360
            ValueError: If margin is negative
            ValueError: If speed is not between 0.0 and 1.0
            ValueError: If direction is not DIRECTION.CW or DIRECTION.CCW
        """

        if target_angle < 0 or target_angle >= 360:
            try:
                raise ValueError("Target angle must be between 0 and 360 degrees.")
            except ValueError as e:
                logger.error(f"Value Error: {e}. No rotation will be performed.")
                return

        if margin < 0:
            try:
                raise ValueError("Margin must be nonnegative")
            except ValueError as e:
                logger.error(f"Value Error: {e}. Using default margin of 4 degrees.")
                margin = 4

        logger.debug(f"Rotating from {self.encoder.get_smoothed_angle():.2f}° to {target_angle:.2f}° at max speed {speed}.")

        self.proportional_rotate(speed, target_angle, margin)

    def proportional_rotate(self, speed: float, target_angle: int|float, margin: int = 4) -> None:
        """
        Rotate the servo motor to a specific target angle at a given speed using proportional control.
        Uses EncoderController to measure the angle of rotation, halting when the desired angle is reached.

        Args:
            speed (float): Maximum speed of the servo motor, where 0.0 is stopped and 1.0 is full speed
            direction (DIRECTION): Direction of rotation, either DIRECTION.CW or DIRECTION.CCW
            target_angle (int): Target angle to rotate to, in degrees from 0 to 360
            margin (int): Margin of error for target angle, in degrees
        """
        # Proportional control parameters
        min_speed = 0.15  # Minimum speed to avoid stalling (tune as needed)
        max_speed = speed # Use the user-supplied max speed
        k = 0.02          # Proportional constant (tune as needed)

        self.start()

        while True:
            current_angle = self.encoder.get_smoothed_angle()
            # Calculate shortest angular distance to target (handling wrap-around)
            error = (target_angle - current_angle + 540) % 360 - 180  # Range: [-180, 180]
            abs_error = abs(error)

            # Proportional speed control: slow down as you get closer
            prop_speed = min(max_speed, max(min_speed, k * abs_error))
            prop_direction = DIRECTION.CCW if error > 0 else DIRECTION.CW
            self.change(prop_speed, prop_direction)

            logger.debug(f"Current Angle: {current_angle:.2f}°, Target Angle: {target_angle:.2f}°, Error: {error:.2f}°, Speed: {prop_speed:.2f}, Direction: {prop_direction.name}")

            if abs_error <= margin:
                logger.debug(f"Current angle: {current_angle:.2f}° within margin ({margin}°). Halting.")
                self.stop()

                timer.wait(0.5)

                double_check_angle = self.encoder.get_smoothed_angle()
                double_check_error = (target_angle - double_check_angle + 540) % 360 - 180  # Range: [-180, 180]
                abs_double_check_error = abs(double_check_error)

                if abs_double_check_error <= margin:
                    logger.debug(f"Double-check successful. Final angle: {double_check_angle:.2f}° within margin ({margin}°).")
                    logger.debug(f"Rotation complete. Final angle: {double_check_angle:.2f}°. Target: {target_angle:.2f}°. Error: {double_check_error:.2f}°.")
                    break
                else:
                    self.start()  # Restart the servo to correct any overshoot
                    logger.debug(f"Double-check failed. Final angle: {self.encoder.get_smoothed_angle():.2f}° outside margin ({margin}°). Restarting servo to correct overshoot.")

            timer.wait(0.002)   # Sleep for a short time to avoid busy waiting

    def get_duty_cycle(self, speed: float, direction: DIRECTION) -> float:
        """
        Calculates the duty cycle for the servo motor based on speed and direction.
        First, after evaluating the speed and direction, it calculates the pulse width for the requested speed and direction.
        Then, it calculates the duty cycle as the ratio of the the pulse width to the PWM period, expressed as a percentage.

        Args:
            speed (float): Speed of the servo motor, where 0.0 is stopped and 1.0 is full speed
            direction (DIRECTION): Direction of rotation, either DIRECTION.CW or DIRECTION.CCW

        Returns:
            float: Duty cycle percentage for the given speed and direction, where 0% is stopped and 100% is full speed in the specified direction.

        Raises:
            ValueError: If speed is not between 0 and 1
            ValueError: If direction is not DIRECTION.CW or DIRECTION.CCW
        """

        try:
            if speed < 0 or speed > 1: raise ValueError("Speed must be between 0.0 and 1.0")

            if direction == DIRECTION.CW:
                pulse_width = self.stop_pw - ((self.stop_pw - self.cw_pulse_width) * speed)
                return (pulse_width / self.period) * 100  # Return duty cycle percentage
            elif direction == DIRECTION.CCW:
                pulse_width = self.stop_pw + ((self.ccw_pulse_width - self.stop_pw) * speed)
                return (pulse_width / self.period) * 100  # Return duty cycle percentage
            else:
                raise ValueError("Direction must be DIRECTION.CW or DIRECTION.CCW")
        except ValueError as e:
            logger.error(f"Value Error: {e}. Returning duty cycle for stop position.")
            self.speed = 0                  # Update the current speed to 0
            self.direction = DIRECTION.CW   # Reset the direction to CW
            return self.stop_duty_cycle     # Return duty cycle percentage for stop position