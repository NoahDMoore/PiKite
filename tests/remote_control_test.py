import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import asyncio

from pikite.core.logger import set_log_level
from pikite.remote.microdot_server import ControllerServer
from pikite.core.settings import Settings
from pikite.core.lcd_menu import Menu
from pikite.core.input_handler import InputCommand, InputSource, InputHandler
from pikite.remote.remote_input import RemoteInput

set_log_level("DEBUG")

server = ControllerServer()
settings = Settings()
input_handler = InputHandler()
menu = Menu(None, settings, input_handler)
remote_input = RemoteInput(server, input_handler)

def fetch_settings(**kwargs):
    current_settings = settings.format_as_dict()
    menu_settings = menu.format_settings_and_options_as_dict()
    settings_payload = {
        "type": "settings_update",
        "current_settings": current_settings,
        "menu_settings": menu_settings
    }

    server.send(settings_payload)

def update_settings(args):
    for new_setting, new_setting_value in args.get("settings_to_update", {}).items():
        if settings.is_setting(new_setting):
            print(f"Updating setting '{new_setting}' from {settings.get(new_setting)} to new value '{new_setting_value}'")
            settings.set(new_setting, new_setting_value)
            fetch_settings()  # Send updated settings back to client
        else:
            print(f"Attempted to update unknown setting: {new_setting}")

def default_settings(**kwargs):
    settings.load_defaults()
    fetch_settings()  # Send updated settings back to client

input_handler.register("default", InputCommand.FETCH_SETTINGS, fetch_settings)
input_handler.register("default", InputCommand.UPDATE_SETTINGS, update_settings)
input_handler.register("default", InputCommand.LOAD_DEFAULT_SETTINGS, default_settings)

async def main():
    await asyncio.gather(
        server.start(),
        remote_input.start_listening()
    )

if __name__ == "__main__":
    asyncio.run(main())