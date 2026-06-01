from __future__ import annotations
from typing import Callable, TYPE_CHECKING

from pikite.core.modes.pikite_mode import BaseMode, PiKiteMode
from pikite.core.input_handler import InputCommand
from pikite.hardware.display_controller import DisplayController
from pikite.system.system_info import display_system_info

if TYPE_CHECKING:
    from pikite.core.modes.mode_manager import ModeManager

class SystemInfoMode(BaseMode):
    def __init__(
            self,
            app_exit_callback: Callable,
            app_reboot_callback: Callable,
            app_shutdown_callback: Callable,
            button_controller,
            display_controller: DisplayController,
            input_handler,
            mode_manager: ModeManager
        ):
        super().__init__(input_handler, button_controller)
        self.app_shutdown = app_shutdown_callback
        self.app_reboot = app_reboot_callback
        self.app_exit = app_exit_callback
        self.display_controller = display_controller
        self.mode_manager = mode_manager

        self.mode = PiKiteMode.SYSTEM_INFO # Override base mode

    async def run(self):
        display_system_info(self.display_controller) # type: ignore
        await self.exit_event.wait()

    def _register_inputs(self):
        # Map Buttons to InputCommands
        self.button_controller.set_commands(
            next_command=InputCommand.NEXT,
            select_command=InputCommand.SELECT,
            mode=self.mode
        )

        # Register InputHandler Actions
        self.inputs = {
            InputCommand.NEXT:lambda: self.mode_manager.switch_to(PiKiteMode.MENU),
            InputCommand.SELECT: lambda: self.mode_manager.switch_to(PiKiteMode.MENU),
            InputCommand.SHUTDOWN: self.app_shutdown,
            InputCommand.REBOOT: self.app_reboot,
            InputCommand.EXIT: self.app_exit,
        }