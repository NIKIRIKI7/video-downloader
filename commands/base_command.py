from abc import ABC, abstractmethod
from typing import Callable, TYPE_CHECKING

# Импортируем ProcessingContext только для проверки типов, чтобы избежать циклического импорта
if TYPE_CHECKING:
    from model.processing_context import ProcessingContext

# Определяем тип для логгера для ясности
LoggerCallable = Callable[[str], None]

class ActionCommand(ABC):
    """Абстрактный базовый класс для всех команд действий."""

    def __init__(self, logger: LoggerCallable):
        """
        Инициализирует команду.

        Args:
            logger: Функция для логирования сообщений (обычно из ViewModel).
        """
        self.log: LoggerCallable = logger

    @abstractmethod
    def execute(self, context: 'ProcessingContext') -> None:
        """
        Выполняет действие команды, используя данные и настройки из контекста.

        Args:
            context: Контекст данных, общий для команд, включая настройки.
                     Команды читают из и пишут в этот объект.

        Raises:
            Exception: Может вызывать исключения при ошибках (например, FileNotFoundError,
                       subprocess.CalledProcessError, ошибки API, ValueError),
                       которые должны обрабатываться вызывающей стороной (VideoService).
        """
        pass