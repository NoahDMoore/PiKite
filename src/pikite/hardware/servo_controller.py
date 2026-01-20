"""Classes to control continuous rotation and traditional servos for pan and tilt.

This module provides classes for controlling continuous rotation servos and traditional servos
for pan and tilt movements. The `PanServo` class is designed for continuous rotation servos, allowing
for speed and direction control, while the `TiltServo` class is for traditional servos that can be
positioned at specific angles.

Typical usage example:
    tilt = TiltServo()
    pan = PanServo()
"""

from enum import Enum
import time

from rpi_hardware_pwm import HardwarePWM    # type: ignore

from ..core.logger import get_logger
from ..core.timer import Timer

# Setup Logger
logger = get_logger(__name__)

class TiltServo:
    """
    Class to control a traditional servo motor for tilt movements of a camera.
    
    This class allows for controlling a traditional servo motor using PWM signals to set the angle of the servo.
    It supports setting the angle in degrees, where 0 degrees is the minimum position and a specified maximum angle is the maximum position.
    """
    def __init__(self, pwm_channel=0, frequency=50, chip=0, max_angle=180, min_pulse_width=500, max_pulse_width=2500):
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
            raise ValueError("Invalid PWM channel. Use 0 or 1.")
        self.frequency = frequency
        self.chip = chip

        # Initialize the PWM with the specified channel, frequency, and chip, and calculate the period in microseconds
        self.pwm = HardwarePWM(pwm_channel=self.pwm_channel, hz=self.frequency, chip=self.chip)
        self.period = (1 / self.frequency) * 1000000    # PWM Period in microseconds

        # Set the maximum angle and pulse widths for the servo
        self.max_angle = max_angle
        self.min_pulse_width = min_pulse_width
        self.max_pulse_width = max_pulse_width

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
        return self._angle

    @angle.setter
    def angle(self, angle: int = 0) -> None:
        """
        Start the servo motor at a given angle; defaults to 0 degrees.
        
        Args:
            angle (int): Angle in degrees to position the servo, where 0 is the minimum angle and self.max_angle is the maximum angle.
        
        Raises:
            ValueError: If angle is not between 0 and max_angle.
        """
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
    
    def stop(self) -> None:
        """Stops the servo motor by setting the duty cycle to 0%."""
        self.pwm.stop()


class DIRECTION(Enum):
    CW = "cw"   # Clockwise
    CCW = "ccw" # Counter-clockwise


class PanServo:
    """
    Class to control a continuous rotation servo motor for pan movements of a camera.
    
    This class allows for controlling a continuous rotation servo motor using PWM signals to set the speed and direction of rotation.
    It supports setting the speed as a float between 0.0 (stopped) and 1.0 (full speed), and the direction as either clockwise (CW) or counter-clockwise (CCW).
    """
    def __init__(self, pwm_channel=1, frequency=50, chip=0, cw_pulse_width=700, ccw_pulse_width=2300, stop_pulse_width=1500, rotation_time=1):
        """
        Initializes the PanServo with the specified parameters.

        Args:
            pwm_channel (int): The PWM channel to use (0 or 1). Channel 0 uses GPIO 18/12, and Channel 1 uses GPIO 19/13.
            frequency (int): The PWM frequency in Hz, default is 50Hz.
            chip (int): The chip number for the PWM channel, default is 0.
                    As of linux kernel 6.12, chip=0 is used for all Raspberry Pi models.
            cw_pulse_width (int): Pulse width in microseconds for full speed clockwise rotation. Default is based on FS90 continuous rotation servo.
            ccw_pulse_width (int): Pulse width in microseconds for full speed counter-clockwise rotation. Default is based on FS90 continuous rotation servo.
            rotation_time (float): Time in seconds to rotate 360 degrees at full speed, default is 1 second.

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

        # Initialize the PWM with the specified channel, frequency, and chip, and calculate the period in microseconds
        self.pwm = HardwarePWM(pwm_channel=self.pwm_channel, hz=self.frequency, chip=self.chip)
        self.period = (1 / self.frequency) * 1000000    # PWM Period in microseconds

        # Set microsecond pulse widths for full speed clockwise and counter-clockwise, and calculate the stop position pulse width.
        self.cw_pulse_width = cw_pulse_width
        self.ccw_pulse_width = ccw_pulse_width
        self.stop_pw = stop_pulse_width
        
        self.stop_duty_cycle = self.get_duty_cycle(0.0, DIRECTION.CW)   # Duty cycle for stop position
        
        # Initialize timer for rotation duration
        self.timer: Timer = Timer()         # Timer to track rotation time
        self.rotation_time = rotation_time  # Get time in seconds to rotate 360 degrees at full speed from configuration settings, default is 1 second

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
    
    def halt(self) -> None:
        """ Stop the servo motor by setting the duty cycle to the stop position."""
        self.pwm.change_duty_cycle(self.stop_duty_cycle)    # Use CW direction with speed of 0 to stop the servo motor
        self.speed = 0                                      # Update the current speed to 0

    def stop(self) -> None:
        """This method halts the servo motor, stops the PWM signal, and resets the speed and direction."""
        self.halt()                     # Stop the servo motor
        self.pwm.stop()                 # Stop the PWM signal
        self.speed = 0.0                # Reset the speed to 0
        self.direction = DIRECTION.CW   # Reset the direction to CW

    def rotate(self, speed: float, direction: DIRECTION, degrees: int) -> None:
        """
        Rotate the servo motor an approximate number of degrees at a given speed and direction.
        Calculates the duration of rotation based on the given speed and ange of rotation in degrees,
        then starts the servo motor, waits for the calculated duration, and then halts the rotation.

        Args:
            speed (float): Speed of the servo motor, where 0.0 is stopped and 1.0 is full speed
            direction (DIRECTION): Direction of rotation, either DIRECTION.CW or DIRECTION.CCW
            degrees (int): Number of degrees to rotate, must be greater than 0; 360 degrees is a full rotation
        
        Raises:
            ValueError: If degrees is negative
            ValueError: If speed is not between 0.0 and 1.0
            ValueError: If direction is not DIRECTION.CW or DIRECTION.CCW
        """

        if degrees < 0:
            try:
                raise ValueError("Degrees must be nonnegative")
            except ValueError as e:
                logger.error(f"Value Error: {e}. Halting rotation.")
                self.halt()
                return
        
        duration = (degrees / 360) * (self.rotation_time / speed) if speed > 0 else 0.0 # Calculate duration in seconds to rotate the servo 
        self.timer.start()                                                              # Start the timer to track rotation time
        end_time = self.timer.start_time + duration                                     # type: ignore (to suppress mypy warning; start_time cannot be None if timer is running)
        self.change(speed, direction)                                                   # Start the servo motor with the given speed and direction

        while True:                                                                     # Loop until the duration has elapsed
            now = self.timer.time
            remaining = end_time - now
            if remaining <= 0:
                break
            if remaining > 0.01:
                time.sleep(0.005)                                                       # Sleep for a short time to avoid busy waiting unless the remaining time is less than 10ms

        self.halt()                                                                     # Stop the servo motor after the duration has elapsed

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