from pikite.core.capture.capture_manager import CaptureManager
from pikite.core.input_handler import InputCommand
from pikite.core.modes.pikite_mode import BaseMode, PiKiteMode
from pikite.remote.remote_api import RemoteAPI
import pikite.utils.logger as logger_module

# Setup Logger
logger = logger_module.get_logger(__name__)



class CaptureMode(BaseMode):
    def __init__(
            self,
            input_handler,
            button_controller,
            capture_manager: CaptureManager,
            remote_api: RemoteAPI
        ):
        super().__init__(input_handler, button_controller)
        self.capture_manager = capture_manager
        self.remote_api = remote_api
        self.mode = PiKiteMode.CAPTURE # Override base mode
        self.auto_return = True

    async def run(self):
        await self.capture_manager.capture_loop()

    def _register_inputs(self):
        # Map Buttons to InputCommands
        self.button_controller.set_commands(
            next_command=InputCommand.STOP_CAPTURE,
            select_command=InputCommand.STOP_CAPTURE,
            mode=self.mode
        )

        # Register InputHandler Actions
        self.inputs = {
            InputCommand.STOP_CAPTURE: self.capture_manager.request_stop,
            InputCommand.REQUEST_SESSION_INFO: self._tx_session_info
        }

    def _tx_session_info(self):
        session = self.capture_manager.get_current_session()
        if session is not None:
            self.remote_api.tx_session_info(session)
        else:
            logger.warning("Error sending session info. No current capture session reported.")