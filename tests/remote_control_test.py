import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

import asyncio

from pikite.core.constants import CAPTURE_MODES
from pikite.core.input_handler import InputCommand, InputSource, InputScope, InputHandler
from pikite.core.lcd_menu import Menu
from pikite.core.logger import set_log_level
from pikite.remote.microdot_server import ControllerServer
from pikite.core.input_handler import RemoteInput
from pikite.core.settings import Settings
from pikite.system.storage import StorageManager

set_log_level("DEBUG")

server = ControllerServer()
settings = Settings()
input_handler = InputHandler()
menu = Menu(None, settings, input_handler)
remote_input = RemoteInput(server, input_handler)
storage_manager = StorageManager()

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

def fetch_media_dirs(**kwargs):
    media_dirs = storage_manager.get_capture_session_dirs()
    media_dirs_payload = {
        "type": "media_dirs_update",
        "media_dirs": media_dirs
    }
    server.send(media_dirs_payload)

def fetch_media(args):
    mode = CAPTURE_MODES.STILL if args.get("mode") == "STILL" else CAPTURE_MODES.VIDEO
    path = args.get("path")
    file_paths = storage_manager.get_capture_session_file_names(mode, path)
    file_paths_payload = {
        "type": "media_file_paths",
        "file_paths": file_paths
    }
    server.send(file_paths_payload)

input_handler.register(InputScope.DEFAULT, InputCommand.FETCH_SETTINGS, fetch_settings)
input_handler.register(InputScope.DEFAULT, InputCommand.UPDATE_SETTINGS, update_settings)
input_handler.register(InputScope.DEFAULT, InputCommand.LOAD_DEFAULT_SETTINGS, default_settings)
input_handler.register(InputScope.DEFAULT, InputCommand.FETCH_MEDIA_DIRS, fetch_media_dirs)
input_handler.register(InputScope.DEFAULT, InputCommand.FETCH_MEDIA, fetch_media)

async def main():
    await asyncio.gather(
        server.start(),
        remote_input.start_listening()
    )

if __name__ == "__main__":
    asyncio.run(main())