from typing import Callable

from pikite.core.modes.pikite_mode import BaseMode, PiKiteMode
from pikite.core.input_handler import InputCommand
from pikite.core.menu import Menu
from pikite.hardware.camera_controller import PreviewStream
from pikite.hardware.pressure_sensor_controller import PressureSensorController
from pikite.hardware.display_controller import DisplayController
from pikite.remote.remote_api import RemoteAPI

class MenuMode(BaseMode):
    def __init__(
            self,
            app_exit_callback: Callable,
            app_reboot_callback: Callable,
            app_shutdown_callback: Callable,
            button_controller,
            camera_preview: PreviewStream,
            input_handler,
            display_controller: DisplayController,
            menu: Menu,
            pressure_sensor: PressureSensorController,
            remote_api: RemoteAPI
        ):
        super().__init__(input_handler, button_controller)
        self.app_exit = app_exit_callback
        self.app_reboot = app_reboot_callback
        self.app_shutdown = app_shutdown_callback
        self.camera_preview = camera_preview
        self.display_controller = display_controller
        self.menu = menu

        self.mode = PiKiteMode.MENU # Override base mode
        self.pressure_sensor = pressure_sensor
        self.remote_api = remote_api

    async def enter(self):
        await super().enter()
        self.menu.update_menu()
        self.camera_preview.start()

    async def run(self):
        await self.mode_change_requested.wait()
        return self.next_mode

    async def exit(self):
        await self.camera_preview.stop()

    def _register_inputs(self):
        # Map Buttons to InputCommands
        self.button_controller.set_commands(
            next_command=InputCommand.NEXT,
            select_command=InputCommand.SELECT,
            mode=self.mode
        )

        # Register InputHandler Actions
        self.inputs = {
            InputCommand.NEXT: self.menu.increment,
            InputCommand.SELECT: self.menu.do_action,
            InputCommand.START_CAPTURE: self.start_capture,
            InputCommand.SET_BASELINE_ALTITUDE: self.get_baseline_pressure,
            InputCommand.DISPLAY_SYSTEM_INFO: self.display_system_info,
            InputCommand.SHUTDOWN: self.app_shutdown,
            InputCommand.REBOOT: self.app_reboot,
            InputCommand.EXIT: self.app_exit,
            InputCommand.FETCH_SETTINGS: self.remote_api.tx_settings,
            InputCommand.UPDATE_SETTINGS: self.remote_api.rx_settings_update,
            InputCommand.LOAD_DEFAULT_SETTINGS: self.remote_api.rx_default_settings_request,
            InputCommand.FETCH_MEDIA_DIRS: self.remote_api.tx_media_dirs,
            InputCommand.FETCH_MEDIA: self.remote_api.tx_media_file_paths,
            InputCommand.PAN: self.remote_api.rx_pan_command,
            InputCommand.TILT: self.remote_api.rx_tilt_command
        }

    def start_capture(self):
        self.request_mode_switch(PiKiteMode.CAPTURE)

    def get_baseline_pressure(self):
        self.request_mode_switch(PiKiteMode.BASELINE_ALTITUDE)

    def display_system_info(self):
        self.request_mode_switch(PiKiteMode.SYSTEM_INFO)