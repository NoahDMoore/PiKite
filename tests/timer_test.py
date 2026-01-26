import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1] / "src"))

from pikite.core.logger import get_logger
from pikite.core.timer import Timer

import time

# Setup Logger
logger = get_logger(__name__)
logger.setLevel("DEBUG")

logger.info("Starting Timer Tests")

def test_timer_start_stop():
    timer = Timer()
    timer.start()
    logger.info("Timer started")
    time.sleep(5)
    elapsed = timer.stop()
    if elapsed is None:
        raise AssertionError("Elapsed time should not be None after stopping the timer")
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
    if paused_elapsed is None:
        raise AssertionError("Elapsed time should not be None when timer is paused")
    assert 2.9 < paused_elapsed < 3.1, f"Elapsed time should be around 3 seconds, got {paused_elapsed}"
    time.sleep(2)  # This should not count towards elapsed time
    timer.resume()
    logger.info("Timer resumed")
    time.sleep(2)
    total_elapsed = timer.stop()
    if total_elapsed is None:
        raise AssertionError("Elapsed time should not be None after stopping the timer")
    assert 4.9 < total_elapsed < 5.1, f"Total elapsed time should be around 5 seconds, got {total_elapsed}"
    logger.info(f"Timer stopped, total elapsed time: {total_elapsed} seconds")

def test_timer_marks():
    timer = Timer()
    timer.start()
    logger.info("Timer started")
    time.sleep(2)
    timer.mark("first_mark")
    logger.info("First mark set")
    time.sleep(3)
    timer.mark("second_mark")
    logger.info("Second mark set")
    time.sleep(1)
    timer.stop()
    first_mark_time = timer.marks.get("first_mark")
    second_mark_time = timer.marks.get("second_mark")
    if first_mark_time is None or second_mark_time is None:
        raise AssertionError("Marks were not recorded properly")
    assert 1.9 < first_mark_time < 2.1, f"First mark time should be around 2 seconds, got {first_mark_time}"
    assert 4.9 < second_mark_time < 5.1, f"Second mark time should be around 5 seconds, got {second_mark_time}"
    logger.info(f"First mark time: {first_mark_time} seconds, Second mark time: {second_mark_time} seconds")