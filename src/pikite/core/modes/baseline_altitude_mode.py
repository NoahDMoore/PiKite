from pikite.core.modes.pikite_mode import BaseMode, PiKiteMode
from pikite.hardware.display_controller import DisplayController
from pikite.hardware.pressure_sensor_controller import PressureSensorController

class BaselineAltitudeMode(BaseMode):
    def __init__(
            self,
            button_controller,
            display_controller: DisplayController,
            input_handler,
            pressure_sensor_controller: PressureSensorController,
        ):
        super().__init__(input_handler, button_controller)
        self.display_controller = display_controller
        self.pressure_sensor_controller = pressure_sensor_controller

        self.mode = PiKiteMode.BASELINE_ALTITUDE # Override base mode
        self.auto_return = True

    async def run(self):
        await self.get_baseline_pressure()

    async def get_baseline_pressure(self):
        self.pressure_sensor_controller.get_baseline_pressure(
            num_samples=80,
            display_controller=self.display_controller
        )