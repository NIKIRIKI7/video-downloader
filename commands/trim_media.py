from commands.base_command import ActionCommand, LoggerCallable # Импортируем LoggerCallable
from utils.utils import get_tool_path
import subprocess
import os
# Не импортируем ProcessingContext, так как эта команда работает иначе

class TrimMedia: # Не наследуем от ActionCommand, т.к. сигнатура execute другая
    """Команда для обрезки видео или аудио файла с использованием ffmpeg."""

    def __init__(self, logger: LoggerCallable):
        """
        Инициализирует команду.

        Args:
            logger: Функция для логирования сообщений.
        """
        self.log: LoggerCallable = logger

    def execute(self, input_path: str, output_path: str, start_time: str, end_time: str) -> None:
        """
        Выполняет обрезку медиафайла.

        Args:
            input_path: Путь к входному файлу.
            output_path: Путь к выходному файлу.
            start_time: Время начала в формате HH:MM:SS[.ms].
            end_time: Время окончания в формате HH:MM:SS[.ms].

        Raises:
            FileNotFoundError: Если ffmpeg или входной файл не найден.
            ValueError: Если временные метки некорректны.
            subprocess.CalledProcessError: Если ffmpeg завершается с ошибкой.
            Exception: При других неожиданных ошибках.
        """
        self.log(f"[TRIM] Начало обрезки файла: {input_path}")
        self.log(f"[TRIM] Время начала: {start_time}")
        self.log(f"[TRIM] Время окончания: {end_time}")
        self.log(f"[TRIM] Выходной файл: {output_path}")

        # --- Валидация ---
        if not os.path.exists(input_path):
            self.log(f"[TRIM][ERROR] Входной файл не найден: {input_path}")
            raise FileNotFoundError(f"Входной файл не найден: {input_path}")

        # Валидация времени была сделана в GUI, но проверим еще раз на всякий случай
        from utils.utils import is_valid_time_format
        if not is_valid_time_format(start_time):
             self.log(f"[TRIM][ERROR] Неверный формат времени начала: {start_time}")
             raise ValueError(f"Неверный формат времени начала: {start_time}")
        if not is_valid_time_format(end_time):
            self.log(f"[TRIM][ERROR] Неверный формат времени окончания: {end_time}")
            raise ValueError(f"Неверный формат времени окончания: {end_time}")

        # Дополнительно: можно сравнить start_time и end_time, но ffmpeg сам справится

        output_dir = os.path.dirname(output_path)
        if output_dir and not os.path.exists(output_dir):
            try:
                os.makedirs(output_dir)
                self.log(f"[TRIM][INFO] Создана выходная директория: {output_dir}")
            except OSError as e:
                self.log(f"[TRIM][ERROR] Не удалось создать выходную директорию {output_dir}: {e}")
                raise

        if os.path.exists(output_path):
             self.log(f"[TRIM][WARN] Выходной файл уже существует: {output_path}. Он будет перезаписан.")
             # ffmpeg с флагом -y перезапишет его

        ffmpeg_path = get_tool_path('ffmpeg') # Вызовет FileNotFoundError, если не найден

        # --- Команда FFmpeg ---
        cmd = [
            ffmpeg_path,
            "-y",               # Перезаписывать выходной файл без запроса
            "-i", input_path,   # Входной файл
            "-ss", start_time,  # Время начала
            "-to", end_time,    # Время окончания
            "-c", "copy",       # Копировать кодеки (быстро, без перекодирования)
                                # Если копирование вызывает проблемы, можно указать кодеки:
                                # "-c:v", "libx264", "-c:a", "aac",
            output_path         # Выходной файл
        ]
        self.log(f"[TRIM][DEBUG] Выполнение команды FFmpeg: {' '.join(cmd)}")

        try:
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            # ffmpeg часто выводит информацию в stderr даже при успехе
            self.log(f"[TRIM][DEBUG] ffmpeg stderr:\n{process.stderr}")
            self.log(f"[TRIM][DEBUG] ffmpeg stdout:\n{process.stdout}")


            if os.path.exists(output_path):
                self.log(f"[TRIM][INFO] Файл успешно обрезан: {output_path}")
            else:
                # Это странная ситуация: ffmpeg завершился успешно, но файла нет
                self.log(f"[TRIM][ERROR] Выходной файл не найден после успешного выполнения ffmpeg: {output_path}")
                raise FileNotFoundError(f"Выходной файл не найден после успешного выполнения ffmpeg: {output_path}")

        except subprocess.CalledProcessError as e:
            self.log(f"[TRIM][ERROR] ffmpeg завершился с ошибкой во время обрезки: {e}")
            self.log(f"[TRIM][ERROR] Команда: {' '.join(cmd)}")
            stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
            self.log(f"[TRIM][ERROR] Stderr: {stderr_output}")
            raise # Перевыбрасываем ошибку выполнения процесса
        except Exception as e:
            self.log(f"[TRIM][ERROR] Неожиданная ошибка во время обрезки: {type(e).__name__} - {e}")
            raise # Перевыбрасываем другие ошибки