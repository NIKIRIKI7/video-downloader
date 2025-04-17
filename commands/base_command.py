from abc import ABC, abstractmethod
from typing import Callable
# Import ProcessingContext for type hinting in execute method signature
from model.processing_context import ProcessingContext

# Define type for logger for clarity
LoggerCallable = Callable[[str], None]

class ActionCommand(ABC):
    """Abstract base class for all action commands."""

    def __init__(self, logger: LoggerCallable):
        """
        Initializes the command.

        Args:
            logger: Function to log messages (typically from ViewModel).
        """
        self.log: LoggerCallable = logger

    @abstractmethod
    def execute(self, context: ProcessingContext) -> None:
        """
        Executes the command's action using data and settings from the context.

        Args:
            context: The data context shared between commands, including settings.
                     Commands read from and write to this object.

        Raises:
            Exception: Can raise exceptions on errors (e.g., FileNotFoundError,
                       subprocess.CalledProcessError, API errors, ValueError),
                       which should be handled by the caller (VideoService).
        """
        pass