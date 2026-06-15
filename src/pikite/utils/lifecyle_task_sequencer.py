from __future__ import annotations  # postpones evaluation so types aren't checked at runtime

from dataclasses import dataclass
from enum import Enum
from inspect import isawaitable
from typing import Any, Callable, List, TYPE_CHECKING

from pikite.utils.logger import get_logger

if TYPE_CHECKING:
    from logging import Logger
    from pikite.hardware.display.loading_bar import LoadingBar

class LifecycleBehavior(str, Enum):
    STARTUP = "startup"
    SHUTDOWN = "shutdown"

@dataclass
class LifecycleStep:
    name: str
    startup: Callable[[], Any] | None
    shutdown: Callable[[], Any] | None
    weight: int = 1

async def startup(
    lifecycle_steps: List[LifecycleStep],
    progress_bar: LoadingBar | None = None,
    hide_last_update: bool = False,
    parent_logger: Logger | None = None
):
    logger = parent_logger or get_logger(__name__)

    await run_task_sequence(
        lifecycle_steps = lifecycle_steps,
        behavior = LifecycleBehavior.STARTUP,
        progress_bar = progress_bar,
        hide_last_update = hide_last_update,
        logger = logger
    )

async def shutdown(
    lifecycle_steps: List[LifecycleStep],
    progress_bar: LoadingBar | None = None,
    hide_last_update: bool = False,
    parent_logger: Logger | None = None
):
    logger = parent_logger or get_logger(__name__)

    await run_task_sequence(
        lifecycle_steps = lifecycle_steps[::-1], # Reverse list of LifecycleSteps for shutdown
        behavior = LifecycleBehavior.SHUTDOWN,
        progress_bar = progress_bar,
        hide_last_update = hide_last_update,
        logger = logger
    )

async def run_task_sequence(
        lifecycle_steps: List[LifecycleStep],
        behavior: LifecycleBehavior,
        logger: Logger,
        progress_bar: LoadingBar | None = None,
        hide_last_update: bool = False,
    ):
    if not isinstance(behavior, LifecycleBehavior):
        logger.error(f"Cannot run task sequence. Invalid behavior specified [{behavior}]")
        return
    
    if not isinstance(lifecycle_steps, List) or lifecycle_steps == []:
        logger.error("No lifecycle steps provided.")
        return

    # If hide_last_update is True, don't count the last task for progress tracking
    num_visible_steps = len(lifecycle_steps) - 1 if hide_last_update else len(lifecycle_steps)

    # Track weight for progress monitoring
    total_weight = 0
    for step in lifecycle_steps[:num_visible_steps]:
        if getattr(step, behavior) is None:
            continue
        total_weight += step.weight
    completed_weight = 0

    # Call Each Task
    for i, step in enumerate(lifecycle_steps):
        task = getattr(step, behavior)

        if task is None:
            logger.debug(f"No task identified for LifecycleStep '{step.name}'")
            continue

        try:
            result = task()

            if isawaitable(result):
                await result
        except Exception:
            logger.exception(f"Failed to execute task '{task.__name__ if hasattr(task, '__name__') else task}' for step '{step.name}'")
        finally: # Handle Progres Monitoring
            if num_visible_steps == 0:
                break

            if hide_last_update and i == len(lifecycle_steps) - 1:
                break

            # Advance the progress bar
            if progress_bar is not None:
                completed_weight += step.weight

                target_progress = round((completed_weight / total_weight) * 100)
                advance_amount = target_progress - progress_bar.value

                print(f"PROGRESS UPDATE by {advance_amount}")
                progress_bar.advance(advance_amount)

    if progress_bar is not None and progress_bar.value < 100:
        # Advance remaining space on progress bar.
        progress_bar.advance(100 - progress_bar.value)

    logger.info(f"PiKite {behavior.value} sequence complete.")