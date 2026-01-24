import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.core.lcd_menu import Menu
from pikite.core.settings import Settings
from pikite.hardware.display_controller import DisplayController

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting Menu Tests")

def test_menu_initialization():
    settings = Settings()
    display_controller = DisplayController()
    menu = Menu(display_controller, settings)
    assert menu is not None
    logger.info("Menu initialized successfully")