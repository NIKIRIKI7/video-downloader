from abc import ABC, abstractmethod
from typing import Dict, Any, Callable

# Определим тип для логгера для ясности
LoggerCallable = Callable[[str], None]

class ActionCommand(ABC):
    """Абстрактный базовый класс для всех команд действий."""

    def __init__(self, logger: LoggerCallable):
        """
        Инициализатор команды.

        Args:
            logger: Функция для логирования сообщений.
        """
        self.log: LoggerCallable = logger

    @abstractmethod
    def execute(self, context: Dict[str, Any]) -> None:
        """
        Выполняет действие команды.

        Args:
            context: Словарь с данными, передаваемый между командами.
                     Ожидается, что команды могут читать и изменять этот словарь.

        Raises:
            Exception: Может выбрасывать исключения в случае ошибок выполнения.
                       Эти ошибки должны обрабатываться вызывающей стороной (например, VideoService).
        """
        pass