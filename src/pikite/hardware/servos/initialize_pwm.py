from rpi_hardware_pwm import HardwarePWM    # type: ignore

from pikite.utils.logger import get_logger
from pikite.utils.timer import Timer

# Setup Logger
logger = get_logger(__name__)

# Initialize Timer
timer = Timer()

def initialize_pwm(pwm_channel: int, frequency: int, chip: int, retries: int = 2) -> HardwarePWM:
    """
    Initializes the HardwarePWM with the specified channel, frequency, and chip.

    Args:
        pwm_channel (int): The PWM channel to use (0 or 1). Channel 0 uses GPIO 18/12, and Channel 1 uses GPIO 19/13.
        frequency (int): The PWM frequency in Hz.
        chip (int): The chip number for the PWM channel.

    Returns:
        HardwarePWM: An instance of the initialized HardwarePWM.

    Raises:
        ValueError: If pwm_channel is not 0 or 1.
    """
    if pwm_channel in [0, 1]:
        for attempt in range(retries):
            try:
                return HardwarePWM(
                    pwm_channel=pwm_channel,
                    hz=frequency,
                    chip=chip
                )
            except PermissionError as e:
                if attempt == retries - 1:
                    raise
                timer.wait(0.1)
    else:
        try:
            raise ValueError("Invalid PWM channel. Use 0 or 1.")
        except ValueError as e:
            logger.critical(f"Value Error: {e}.")
            raise

