import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.core.timer import Timer

import time

# Setup Logger
logger = get_logger(__name__)

logger.info("Starting Timer Tests")

def test_timer_start_stop():
    timer = Timer()
    timer.start()
    logger.info("Timer started")
    time.sleep(5)
    elapsed = timer.stop()
    assert 4.9 < elapsed < 5.1, f"Elapsed time should be around 5 seconds, got {elapsed}"
    logger.info(f"Timer stopped, elapsed time: {elapsed} seconds")