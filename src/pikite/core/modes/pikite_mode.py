from __future__ import annotations  # postpones evaluation so types aren't checked at runtime
import asyncio
from abc import ABC, abstractmethod
from enum import Enum, auto
from typing import TYPE_CHECKING, Callable

import pikite.utils.logger as logger_module

if TYPE_CHECKING:
    from pikite.core.input_handler import InputHandler, InputCommand
    from pikite.hardware.button_controller import ButtonController

class PiKiteMode(str, Enum):
    DEFAULT = "default"
    MENU = "menu"
    CAPTURE = "capture"
    SYSTEM_INFO = "system_info"

class BaseMode(ABC):
    def __init__(self,
            input_handler: InputHandler,
            button_controller: ButtonController,
        ):
        self.input_handler = input_handler
        self.button_controller = button_controller

        # Setup Logger
        self.logger = logger_module.get_logger(self.__class__.__name__)
        
        self.mode = PiKiteMode.DEFAULT
        self.auto_return = False                    # Return to previous mode on completion.
        self.next_mode: PiKiteMode | None = None
        self.exit_event = asyncio.Event()
        self.inputs: dict[InputCommand, Callable] = {}

    async def enter(self):
        self.exit_event.clear()
        await asyncio.sleep(0)

    @abstractmethod
    async def run(self):
        raise NotImplementedError

    async def exit(self):
        self.exit_event.set()

    def _register_inputs(self):
        pass

    def _input_registry_factory(self):
        if not self.inputs:
            self.logger.debug(f"{self.__class__.__name__} has no InputCommand callbacks to register.")

        self.logger.info(f"Registering {len(self.inputs)} InputCommand callbacks.")

        for input_command, callback in self.inputs.items():
            self.input_handler.register(
                mode=self.mode,
                command=input_command,
                callback=callback
            )

            self.logger.debug(f"Registered callback: {callback.__qualname__} for InputCommand: {input_command} in mode: {self.mode.name}")

        self.logger.info(f"Successfully registered {len(self.inputs)} InputCommand callbacks.")

    def initialize_inputs(self):
        self._register_inputs()
        self._input_registry_factory()