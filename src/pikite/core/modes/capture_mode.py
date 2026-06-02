from pikite.core.modes.pikite_mode import BaseMode, PiKiteMode
from pikite.core.input_handler import InputCommand
from pikite.core.capture_manager import CaptureManager

class CaptureMode(BaseMode):
    def __init__(
            self,
            input_handler,
            button_controller,
            capture_manager: CaptureManager,
        ):
        super().__init__(input_handler, button_controller)
        self.capture_manager = capture_manager
        self.mode = PiKiteMode.CAPTURE # Override base mode
        self.auto_return = True

    async def run(self):
        await self.capture_manager.capture_loop()
        return self.next_mode

    def _register_inputs(self):
        # Map Buttons to InputCommands
        self.button_controller.set_commands(
            next_command=InputCommand.STOP_CAPTURE,
            select_command=InputCommand.STOP_CAPTURE,
            mode=self.mode
        )

        # Register InputHandler Actions
        self.inputs = {
            InputCommand.STOP_CAPTURE: self.capture_manager.request_stop
        }