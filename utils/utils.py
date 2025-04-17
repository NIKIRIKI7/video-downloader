# File: utils/utils.py

import os
import shutil
from typing import Optional
import re # Добавлено для валидации времени

# import constants

def ensure_dir(path: str) -> None:
    """
    Создает директорию по указанному пути, если она не существует.
    Вызывает OSError при ошибке создания.
    """
    if not os.path.isdir(path):
        try:
            os.makedirs(path, exist_ok=True)
            print(f"[INFO] Создана директория: {path}")
        except OSError as e:
            print(f"[ERROR] Не удалось создать директорию {path}: {e}")
            raise

def find_executable(name: str, configured_path: Optional[str]) -> Optional[str]:
    """
    Находит путь к исполняемому файлу для данного инструмента.
    Сначала проверяет настроенный путь, затем ищет в системном PATH.

    Args:
        name: Имя исполняемого файла (например, 'ffmpeg', 'yt-dlp').
        configured_path: Путь, указанный в constants.py (или None/пустой).

    Returns:
        Полный путь к исполняемому файлу, если он найден и исполняем, иначе None.
    """
    if configured_path and os.path.isfile(configured_path):
        if os.access(configured_path, os.X_OK):
             return configured_path
        else:
            print(f"[WARN] Настроенный путь для '{name}' существует, но не является исполняемым: {configured_path}")

    found_path = shutil.which(name)
    if found_path:
        return found_path

    return None

def get_tool_path(tool_name: str) -> str:
    """
    Получает путь для необходимого инструмента (например, 'ffmpeg', 'yt-dlp'),
    проверяя сначала константы на наличие настроенного пути, затем системный PATH.

    Args:
        tool_name: Имя инструмента.

    Returns:
        Полный путь к исполняемому файлу.

    Raises:
        FileNotFoundError: Если инструмент не найден.
    """
    import constants
    path_const_name = f"{tool_name.upper()}_PATH"
    configured_path = getattr(constants, path_const_name, None)

    path = find_executable(tool_name, configured_path)
    if not path:
        error_message = (
            f"Необходимый инструмент '{tool_name}' не найден.\n"
            f"Убедитесь, что он установлен и добавлен в переменную среды PATH вашей системы.\n"
            f"Либо укажите полный путь к исполняемому файлу "
            f"в файле 'constants.py' с помощью переменной '{path_const_name}'."
        )
        raise FileNotFoundError(error_message)
    return path

def is_valid_time_format(time_str: str) -> bool:
    """
    Проверяет, соответствует ли строка формату HH:MM:SS или HH:MM:SS.ms.
    """
    pattern = re.compile(r"^\d{2}:\d{2}:\d{2}(\.\d{1,3})?$")
    return bool(pattern.match(time_str))

def generate_trimmed_filename(input_path: str, start_time: str, end_time: str) -> str:
    """
    Генерирует имя выходного файла для обрезанного медиа.
    Пример: input.mp4 -> input_trimmed_00-01-00_00-05-30.mp4
    """
    base, ext = os.path.splitext(input_path)
    # Очистка временных строк для имени файла
    start_clean = start_time.replace(":", "-").replace(".", "-")
    end_clean = end_time.replace(":", "-").replace(".", "-")
    return f"{base}_trimmed_{start_clean}_{end_clean}{ext}"