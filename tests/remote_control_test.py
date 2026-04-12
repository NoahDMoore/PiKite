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

def fetch_settings():
    current_settings = settings.format_as_dict()
    menu_settings = menu.format_settings_and_options_as_dict()
    settings_payload = {
        "type": "settings_update",
        "current_settings": current_settings,
        "menu_settings": menu_settings
    }

    server.send(settings_payload)

input_handler.register("default", InputCommand.FETCH_SETTINGS, fetch_settings)

async def main():
    await asyncio.gather(
        server.start(),
        remote_input.start_listening()
    )

if __name__ == "__main__":
    asyncio.run(main())