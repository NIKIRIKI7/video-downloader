# File: commands/trim_media.py

from commands.base_command import LoggerCallable
from utils.utils import get_tool_path, is_valid_time_format
from pathlib import Path
import subprocess

class TrimMedia:
    """Команда для обрезки медиа-файла (видео или аудио) с помощью ffmpeg."""

    def __init__(self, logger: LoggerCallable) -> None:
        """Инициализация с передачей функции логирования."""
        self.log = logger

    def execute(self, input_path: Path | str, output_path: Path | str, start_time: str, end_time: str) -> None:
        """
        Обрезает медиа-файл с timecode start_time до end_time без перекодирования.

        Args:
            input_path: Путь к входному файлу (Path или str).
            output_path: Путь к выходному файлу (Path или str).
            start_time: Время начала в формате HH:MM:SS[.ms].
            end_time: Время окончания в формате HH:MM:SS[.ms].

        Raises:
            FileNotFoundError: если файл не существует или ffmpeg не найден.
            ValueError: если форматы времени некорректны.
            subprocess.CalledProcessError: если ffmpeg завершается с ошибкой.
        """
        inp = Path(input_path)
        out = Path(output_path)

        self.log(f"[TRIM] Входной файл: {inp}")
        self.log(f"[TRIM] Выходной файл: {out}")
        self.log(f"[TRIM] Начало: {start_time}, Конец: {end_time}")

        # Проверка наличия входного файла
        if not inp.exists():
            self.log(f"[TRIM][ERROR] Входной файл не найден: {inp}")
            raise FileNotFoundError(f"Входной файл не найден: {inp}")

        # Валидация формата времени
        if not is_valid_time_format(start_time):
            self.log(f"[TRIM][ERROR] Неверный формат времени начала: {start_time}")
            raise ValueError(f"Неверный формат времени начала: {start_time}")
        if not is_valid_time_format(end_time):
            self.log(f"[TRIM][ERROR] Неверный формат времени окончания: {end_time}")
            raise ValueError(f"Неверный формат времени окончания: {end_time}")

        # Создаем директорию выхода, если нужно
        out_dir = out.parent
        if out_dir and not out_dir.exists():
            out_dir.mkdir(parents=True, exist_ok=True)
            self.log(f"[TRIM][INFO] Создана директория для выхода: {out_dir}")

        # ffmpeg путь
        ffmpeg = get_tool_path('ffmpeg')

        # Собираем команду
        cmd = [
            str(ffmpeg), '-y',
            '-i', str(inp),
            '-ss', start_time,
            '-to', end_time,
            '-c', 'copy',
            str(out)
        ]
        self.log(f"[TRIM][DEBUG] Выполнение: {' '.join(cmd)}")

        # Запуск ffmpeg
        try:
            proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
            # ffmpeg пишет инфо в stderr
            self.log(f"[TRIM][DEBUG] ffmpeg stderr:\n{proc.stderr}")
            if out.exists():
                self.log(f"[TRIM][INFO] Обрезка успешна: {out}")
            else:
                self.log(f"[TRIM][ERROR] Выходной файл не найден после обрезки: {out}")
                raise FileNotFoundError(f"Выходной файл не найден: {out}")
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ''
            self.log(f"[TRIM][ERROR] ffmpeg error: {stderr}")
            raise
        except Exception:
            raise
