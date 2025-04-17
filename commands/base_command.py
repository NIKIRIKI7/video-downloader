from abc import ABC, abstractmethod
from typing import Callable
from model.processing_context import ProcessingContext # Import the context object

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
        Executes the command's action.

        Args:
            context: The data context shared between commands.
                     Commands read from and write to this object.

        Raises:
            Exception: Can raise exceptions on errors (e.g., FileNotFoundError,
                       subprocess.CalledProcessError, API errors), which should
                       be handled by the caller (VideoService).
        """
        pass