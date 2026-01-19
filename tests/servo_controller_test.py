import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting Servo Controller Tests")