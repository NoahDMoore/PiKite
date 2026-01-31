"""Timer utility for measuring elapsed time and intervals.

This module provides a Timer class that can be used to track elapsed time,
and check if specific intervals have passed. Uses the `time.perf_counter()`
function for high-resolution timing.
"""

import time
import datetime
from enum import Enum, auto
from .logger import get_logger

logger = get_logger(__name__)

class TimerState(Enum):
    STOPPED = auto()
    RUNNING = auto()
    PAUSED = auto()

class Timer:
    def __init__(self):
        """Initializes the Timer."""
        self.start_time: float | None = None            # Used to store the time when the timer was started, reset, or resumed
        self.initial_start_time: float | None = None    # Used to store the time when the timer was started
        self.paused_time: float | None = None
        self.accumulated: float = 0.0
        self.marks: dict[str, float | None] = {}
        self.named_intervals: dict[str, float] = {}
        self.state: TimerState = TimerState.STOPPED
        logger.debug("Timer instance created")

    @property
    def time(self) -> float:
        """Returns the current high-resolution time in seconds."""
        return time.perf_counter()
    
    @property
    def running(self) -> bool:
        """Returns True if the timer is currently running, False otherwise."""
        return self.state == TimerState.RUNNING
    
    @running.setter
    def running(self, value: bool):
        """Sets the timer to running or stopped state based on the supplied boolean value."""
        if value:
            self.start()
        else:
            self.stop()

    @property
    def paused(self) -> bool:
        """Returns True if the timer is currently paused, False otherwise."""
        return self.state == TimerState.PAUSED
    
    @paused.setter
    def paused(self, value: bool):
        """Sets the timer to paused or resumed state based on the supplied boolean value."""
        if value:
            self.pause()
        else:
            self.resume()
    
    @property
    def stopped(self) -> bool:
        """Returns True if the timer is currently stopped, False otherwise."""
        return self.state == TimerState.STOPPED

    def start(self):
        """Starts the timer."""
        if self.running or self.paused:
            logger.warning("Timer is already started. Cannot start again.")
            return
        else:
            self.start_time = self.time
            self.initial_start_time = self.start_time
            self.paused_time = None
            self.accumulated = 0.0
            self.marks.clear()
            self.named_intervals.clear()
            self.state = TimerState.RUNNING
            logger.debug("Timer started")

    def reset(self, clear_intervals: bool = True):
        """Resets the current timer state."""
        self.start_time = self.time if self.running or self.paused else None   # Sets start_time to current time if running, otherwise None
        self.initial_start_time = self.start_time
        self.paused_time = None
        self.accumulated = 0.0
        self.marks.clear()

        if clear_intervals:
            self.named_intervals.clear()
        else:
            for name in self.named_intervals:
                self.set_named_interval(name)  # Update named intervals to the based on the new start time
        
        if self.paused:
            self.state = TimerState.RUNNING  # If paused, set the state to RUNNING, otherwise keep the current state

    def stop(self) -> float | None:
        """Stops the timer and returns the total elapsed time."""
        if self.stopped:
            logger.warning("Timer is not running. Cannot stop.")
            return None
        else:
            elapsed = self.elapsed()
            self.start_time = None
            self.initial_start_time = None
            self.paused_time = None
            self.accumulated = 0.0
            self.marks.clear()
            self.named_intervals.clear()
            self.state = TimerState.STOPPED
            logger.debug(f"Timer stopped. Elapsed time: {elapsed:.3f}s")
            return elapsed
    
    def pause(self):
        """Pauses the timer."""
        if self.running:
            self.paused_time = self.time
            self.accumulated += (self.paused_time - self.start_time)  # type: ignore (to suppress mypy warning; start_time and paused_time cannot be None if running is True)
            self.start_time = None
            self.state = TimerState.PAUSED
            logger.debug(f"Timer paused. Accumulated time: {self.accumulated:.3f}s")
        elif self.stopped:
            logger.warning("Timer is not running. Cannot pause.")
            return
        else:
            logger.warning("Timer is already paused.")
            return
    
    def resume(self):
        """Resumes the timer if it is paused."""
        if self.paused:
            self.start_time = self.time
            self.paused_time = None
            self.state = TimerState.RUNNING
            logger.debug("Timer resumed")
        elif self.running:
            logger.warning("Timer is already running.")
            return
        else:
            logger.warning("Timer is not paused.")
            return

    def elapsed(self) -> float | None:
        """Returns total elapsed time, excluding paused durations.
        
        Returns:
            float | None: Total elapsed time in seconds, or None if the timer is stopped.
        
        """
        if self.running:
            return self.accumulated + (self.time - self.start_time)     # type: ignore (to suppress mypy warning; start_time cannot be None if running is True)
        elif self.paused:
            return self.accumulated
        else:
            logger.warning("Timer is not running or paused. Cannot calculate elapsed time.")
            return None
    
    def mark(self, name: str) -> None:
        """Sets a mark with the current time.

        Args:
            name (str): The name of the mark.
        """
        if self.running or self.paused:
            self.marks[name] = self.elapsed()
            logger.debug(f"Mark '{name}' set at {self.marks[name]:.3f}s")
        else:
            logger.warning("Timer is not running or paused. Cannot set mark.")

    def since_mark(self, name: str) -> float | None:
        """Returns the time since a specific mark.

        Args:
            name (str): The name of the mark.

        Returns:
            float | None: Time in seconds since the mark was set, or None if the mark does not exist.
        """
        if self.stopped:
            logger.warning("Timer is not running or paused. Cannot calculate time since mark.")
            return None

        mark = self.marks.get(name, None)
        if mark is not None:
            time_since = self.elapsed() - mark    # type: ignore (to suppress mypy warning; elapsed() cannot return None if the timer is running or paused)
            logger.debug(f"Time since mark '{name}': {time_since:.3f}s")
            return time_since
        else:
            logger.warning(f"Mark '{name}' does not exist.")
            return None

    def set_named_interval(self, name: str) -> None:
        """Creates a named interval with the total elapsed time.

        Args:
            name (str): The name of the interval.
        """
        if self.running or self.paused:
            self.named_intervals[name] = self.elapsed()     # type: ignore (to suppress mypy warning; elapsed() cannot return None if the timer is running or paused)
            logger.debug(f"Named interval '{name}' set at {self.named_intervals[name]:.3f}s")
        else:
            logger.warning("Timer is not running or paused. Cannot create named interval.")

    def interval_elapsed(self, interval: float, name: str = "_default", catch_up: bool = True) -> bool:
        """Checks if the specified interval has passed since the last check.

        Args:
            interval (float): The interval in seconds to check against.
            name (str): The name of the interval to check. Defaults to "_default".
            catch_up (bool): If True, advances named_interval time by the interval;
                This prevents drift; otherwise the named_interval is set to the elapsed time.

        Returns:
            bool: True if the interval has passed, False otherwise.
        """
        if self.stopped or self.paused:
            return False

        last_interval_time = self.named_intervals.get(name, None)

        if last_interval_time is None:
            logger.debug(f"Interval '{name}' does not exist. Creating a new one.")
            self.set_named_interval(name)
            return False
        
        elapsed_time = self.elapsed()

        if elapsed_time is None:
            logger.warning("Timer is not running or paused. Cannot check interval.")
            return False
        
        # Check if the specified interval has passed
        if elapsed_time - last_interval_time >= interval:
            self.named_intervals[name] = last_interval_time + interval if catch_up else elapsed_time
            logger.debug(f"Interval '{name}' elapsed. Next check in {interval:.3f}s")
            return True
        else:
            return False
        
    def format_elapsed_time(self, time_in_seconds):
        """
        Converts elapsed time, given in seconds, to a string with format hh:mm:ss

        Args:
            time_in_seconds (float): The elapsed time, in seconds, to be formatted.

        Returns:
            string: Elapsed time formatted as hh:mm:ss
        """
        minutes, seconds = divmod(time_in_seconds, 60)
        hours, minutes = divmod(minutes, 60)

        # Format with leading zeros (padding) using f-string
        time_string = f"{hours:02d}:{minutes:02d}:{seconds:02d}"

        return time_string