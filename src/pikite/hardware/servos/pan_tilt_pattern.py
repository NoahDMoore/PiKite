from pikite.hardware.servos.pan_servo import PanServo
from pikite.hardware.servos.tilt_servo import TiltServo
from pikite.utils.timer import Timer

from enum import Enum

class PanTiltPattern:
    """
    Pans and/or Tilts the PiKite rig at set
    intervals and according to predefined patterns
    """
    class PAN_TILT_MODES(str, Enum):
        """
        Pan/Tilt modes supported by PiKite. 
        """

        NONE = "none"
        PAN_30 = "pan_30"       # Pan in 30 degree increments
        PAN_45 = "pan_45"       # Pan in 45 degree increments
        PAN_90 = "pan_90"       # Pan in 90 degree increments
        TILT_30 = "tilt_30"     # Tilt in 90 degree increments
        TILT_45 = "tilt_45"     # Tilt in 90 degree increments
        GRID_180 = "grid_180"   # Pan and Tilt within a 7x4 grid across 180 degrees
        GRID_360 = "grid_360"   # Pan and Tilt within a 12x4 grid across 360 degrees

    MODE_PARAMETERS = {
        # pan_step (int): Number of degrees to pan each step
        # tilt_step (int): Number of degrees to tilt each step
        # pan_limit (int): Degrees of rotation before reversing direction.
        #                  Max 360 degrees. Should be divisible by pan_step.
        # tilt_limit (int): Degrees of tilt before reversing direction.
        #                   Max 90 degrees. Should be divisible by tilt_step

        PAN_TILT_MODES.NONE: {"pan_step": 0, "tilt_step": 0, "pan_limit": 0, "tilt_limit": 0},
        PAN_TILT_MODES.PAN_30: {"pan_step": 30, "tilt_step": 0, "pan_limit": 360, "tilt_limit": 0},
        PAN_TILT_MODES.PAN_45: {"pan_step": 45, "tilt_step": 0, "pan_limit": 360, "tilt_limit": 0},
        PAN_TILT_MODES.PAN_90: {"pan_step": 90, "tilt_step": 0, "pan_limit": 360, "tilt_limit": 0},
        PAN_TILT_MODES.TILT_30: {"pan_step": 0, "tilt_step": 30, "pan_limit": 0, "tilt_limit": 90},
        PAN_TILT_MODES.TILT_45: {"pan_step": 0, "tilt_step": 45, "pan_limit": 0, "tilt_limit": 90},
        PAN_TILT_MODES.GRID_180: {"pan_step": 30, "tilt_step": 30, "pan_limit": 180, "tilt_limit": 90},
        PAN_TILT_MODES.GRID_360: {"pan_step": 30, "tilt_step": 30, "pan_limit": 360, "tilt_limit": 90},
    }

    def __init__(self, mode: PAN_TILT_MODES, pan_servo: PanServo, tilt_servo: TiltServo):
        self.mode = mode
        self.pan_servo = pan_servo
        self.tilt_servo = tilt_servo
        if self.pan_servo is None or self.tilt_servo is None:
            raise TypeError("pan_servo must be of type PanServo and tilt_servo must of type TiltServo")

        self.PAN_STEP = PanTiltPattern.MODE_PARAMETERS[self.mode]["pan_step"]
        self.TILT_STEP = PanTiltPattern.MODE_PARAMETERS[self.mode]["tilt_step"]
        self.PAN_LIMIT = PanTiltPattern.MODE_PARAMETERS[self.mode]["pan_limit"]
        self.TILT_LIMIT = PanTiltPattern.MODE_PARAMETERS[self.mode]["tilt_limit"]

        self.current_pan_angle = 0
        self.target_pan_angle = 0

        self.pan_step_sum = 0
        self.tilt_step_sum = 0

        self.pan_reverse = False
        self.tilt_reverse = False

        self.timer = Timer(name=f"{__name__}.{__class__.__name__}")

        self.reset()

    def reset(self):
        self.pan_servo.home()
        self.tilt_servo.home()
        self.current_pan_angle = 0

    def step(self):
        if self.PAN_STEP > 0:
            if not self.pan_reverse:
                self.target_pan_angle = (self.current_pan_angle - self.PAN_STEP) % 360
            else:
                self.target_pan_angle = (self.current_pan_angle + self.PAN_STEP) % 360

            self.pan_servo.rotate_to(
                speed=0.5,
                target_angle=self.target_pan_angle,
                margin=4
            )

            self.current_pan_angle = self.target_pan_angle
            self.pan_step_sum += self.PAN_STEP
            self.timer.wait(0.5) # Wait for the pan movement to complete before moving the tilt servo

        if self.TILT_STEP > 0 and self.pan_step_sum >= self.PAN_LIMIT:
            tilt_delta = self.TILT_STEP if not self.tilt_reverse else -self.TILT_STEP

            self.tilt_servo.angle += tilt_delta

            self.tilt_step_sum += self.TILT_STEP

            if self.tilt_step_sum >= self.TILT_LIMIT:
                self.tilt_step_sum = 0
                self.tilt_reverse = not self.tilt_reverse

        if self.PAN_STEP > 0 and self.pan_step_sum >= self.PAN_LIMIT:
            self.pan_step_sum = 0
            self.pan_reverse = not self.pan_reverse