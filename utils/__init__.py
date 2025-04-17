"""
Модуль утилит проекта. Здесь можно размещать вспомогательные функции,
например: логирование, проверку директорий, загрузку конфигов и т.д.
"""

import os

def ensure_dir(path):
    """Создает директорию, если она не существует."""
    if not os.path.isdir(path):
        os.makedirs(path)

def find_file_by_prefix(prefix, extension=".mp3", directory="."):
    """Ищет первый файл с заданным префиксом и расширением в директории."""
    for fname in os.listdir(directory):
        if fname.startswith(prefix) and fname.endswith(extension):
            return os.path.join(directory, fname)
    return None
