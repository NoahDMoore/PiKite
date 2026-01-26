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

def test_timer_pause_resume():
    timer = Timer()
    timer.start()
    logger.info("Timer started")
    time.sleep(3)
    timer.pause()
    logger.info("Timer paused")
    paused_elapsed = timer.elapsed()
    assert 2.9 < paused_elapsed < 3.1, f"Elapsed time should be around 3 seconds, got {paused_elapsed}"
    time.sleep(2)  # This should not count towards elapsed time
    timer.resume()
    logger.info("Timer resumed")
    time.sleep(2)
    total_elapsed = timer.stop()
    assert 4.9 < total_elapsed < 5.1, f"Total elapsed time should be around 5 seconds, got {total_elapsed}"
    logger.info(f"Timer stopped, total elapsed time: {total_elapsed} seconds")