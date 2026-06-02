from typing import Dict

from pikite.core.input_handler import InputHandler
from pikite.core.modes.pikite_mode import BaseMode, PiKiteMode
from pikite.remote.remote_api import RemoteAPI
from pikite.utils.logger import get_logger

logger = get_logger(__name__)

class ModeManager:
    def __init__(self, input_handler: InputHandler, remote_api: RemoteAPI):
        self.input_handler = input_handler
        self.remote_api = remote_api
        self._modes: Dict[PiKiteMode, BaseMode] = {}
        self._current_mode: BaseMode | None = None
        self._previous_mode: BaseMode | None = None

    def register_mode(self, mode: BaseMode):
        if mode.mode in self._modes:
            logger.warning(f"A Mode has already been registered for {mode.mode}. Registration of {mode.__class__.__name__} aborted.")
            return
        
        self._modes[mode.mode] = mode
        logger.debug(f"Registered {mode.__class__.__qualname__} for mode {mode.mode}.")

    @property
    def current_mode(self) -> BaseMode | None:
        return self._current_mode

    @property
    def current_mode_type(self) -> PiKiteMode | None:
        if self._current_mode is None:
            return None
        return self._current_mode.mode

    async def switch_to(self, mode: PiKiteMode):
        new_mode = self._modes[mode]

        if self._current_mode is new_mode:
            logger.warning(f"Cannot change mode to {new_mode.__class__.__qualname__} because it is already active!")
            return

        if self._current_mode is not None:
            await self._current_mode.exit()

        self._previous_mode = self._current_mode
        self._current_mode = new_mode
        self.input_handler.set_mode(self._current_mode.mode)
        self.remote_api.tx_mode(self._current_mode.mode)

        await self._current_mode.enter()

    async def run_current_mode(self):
        mode = self._current_mode

        if mode is None:
            raise RuntimeError("No active mode.")
        
        try:
            next_mode = await mode.run()
            
            if mode.auto_return and self._previous_mode is not None:
                await self.switch_to(self._previous_mode.mode)
                return
            
            if next_mode is not None:
                await self.switch_to(next_mode)
                return
            
        except NotImplementedError:
            logger.exception(f"Cannot run current mode: {mode.__class__.__name__}. No run method implemented.")

    def request_exit(self):
        logger.info("Exit requested. Shutting down application.")
        if self._current_mode is not None:
            self._current_mode.mode_change_requested.set() # Unblock mode if waiting for mode change to allow clean exit.