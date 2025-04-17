"""
Модуль утилит проекта. Здесь можно размещать вспомогательные функции.
"""

import os
from typing import Optional

def ensure_dir(path: str) -> None:
    """
    Создает директорию по указанному пути, если она не существует.

    Args:
        path: Путь к директории.
    """
    if not os.path.isdir(path):
        try:
            os.makedirs(path)
            print(f"Создана директория: {path}") # Добавим лог для ясности
        except OSError as e:
            print(f"Ошибка при создании директории {path}: {e}")
            # В реальном приложении здесь можно выбросить исключение или обработать иначе