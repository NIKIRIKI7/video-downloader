import os
from pathlib import Path
import shutil
from typing import Optional
import re


def ensure_dir(path: Path | str) -> None:
    """
    Создает директорию по указанному пути, если она не существует.
    Принимает Path или строку.
    Вызывает OSError при ошибке создания.
    """
    p = Path(path)
    try:
        p.mkdir(parents=True, exist_ok=True)
        print(f"[INFO] Создана директория: {p}")
    except OSError as e:
        print(f"[ERROR] Не удалось создать директорию {p}: {e}")
        raise


def find_executable(name: str, configured_path: Optional[str]) -> Optional[Path]:
    """
    Находит путь к исполняемому файлу для данного инструмента.
    Сначала проверяет настроенный путь, затем ищет в системном PATH.

    Args:
        name: Имя исполняемого файла (например, 'ffmpeg', 'yt-dlp').
        configured_path: Путь, указанный в constants.py (или None/пустой).

    Returns:
        Path к исполняемому файлу, если он найден и исполняем, иначе None.
    """
    from shutil import which

    if configured_path:
        cfg = Path(configured_path)
        if cfg.is_file() and os.access(cfg, os.X_OK):
            return cfg
    system_path = which(name)
    return Path(system_path) if system_path else None


def get_tool_path(tool_name: str) -> Path:
    """
    Возвращает Path к инструменту или бросает FileNotFoundError.
    """
    import constants
    path_const = getattr(constants, f"{tool_name.upper()}_PATH", None)
    candidate = find_executable(tool_name, path_const)
    if candidate and candidate.exists():
        return candidate
    raise FileNotFoundError(
        f"Необходимый инструмент '{tool_name}' не найден. "
        f"Проверьте PATH или укажите полный путь в constants.py"
    )


def is_valid_time_format(time_str: str) -> bool:
    """
    Проверяет формат HH:MM:SS или HH:MM:SS.ms.
    """
    pattern = re.compile(r"^\d{2}:\d{2}:\d{2}(\.\d{1,3})?$")
    return bool(pattern.match(time_str))


def generate_trimmed_filename(input_path: Path | str, start_time: str, end_time: str) -> str:
    """
    Генерирует имя выходного файла для обрезанного медиа.
    Пример: input.mp4 -> input_trimmed_00-01-00_00-05-30.mp4
    """
    p = Path(input_path)
    base = p.stem
    ext = p.suffix
    start_clean = start_time.replace(':', '-').replace('.', '-')
    end_clean = end_time.replace(':', '-').replace('.', '-')
    return f"{base}_trimmed_{start_clean}_{end_clean}{ext}"
