from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
import os

class DownloadVideo(ActionCommand):
    """Команда для скачивания самого видео с использованием yt-dlp, на основе настроек контекста."""

    def execute(self, context: ProcessingContext) -> None:
        """Скачивает видеофайл в соответствии с настройками формата контекста."""
        if not context.base:
            self.log("[ERROR] Невозможно скачать видео: базовое имя файла 'base' не установлено в контексте.")
            raise ValueError("Базовое имя файла не установлено в контексте перед скачиванием видео.")

        url = context.url
        output_dir = context.output_dir
        ensure_dir(output_dir)

        yt_dlp_format = context.yt_dlp_format
        video_format_ext = context.video_format_ext

        if not yt_dlp_format:
            self.log("[ERROR] Формат скачивания yt-dlp не указан в контексте.")
            raise ValueError("Требуется формат скачивания yt-dlp.")
        if not video_format_ext:
             self.log("[ERROR] Расширение выходного формата видео не указано в контексте.")
             raise ValueError("Требуется расширение выходного формата видео.")

        expected_video_path = context.get_video_filepath()
        if not expected_video_path:
            self.log("[ERROR] Невозможно определить путь к видеофайлу.")
            raise ValueError("Не удалось определить путь к видеофайлу.")

        if os.path.exists(expected_video_path):
             self.log(f"[WARN] Видеофайл уже существует: {expected_video_path}. Пропуск скачивания.")
             context.video_path = expected_video_path
             return

        yt_dlp_path = get_tool_path('yt-dlp')
        output_template = os.path.join(output_dir, f"{context.base}.%(ext)s")

        self.log(f"[INFO] Скачивание видео (формат: '{yt_dlp_format}', контейнер: '{video_format_ext}') в {output_dir}...")
        cmd = [
            yt_dlp_path,
            "--encoding", "utf-8",
            "--no-playlist",
            "--format", yt_dlp_format,
            "--merge-output-format", video_format_ext,
            # Не записывать описание или субтитры здесь, это делают другие команды
            "-o", output_template,
            url
        ]
        self.log(f"[DEBUG] Выполнение команды yt-dlp: {' '.join(cmd)}")

        try:
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

            if os.path.exists(expected_video_path):
                context.video_path = expected_video_path
                self.log(f"[INFO] Видео успешно скачано: {expected_video_path}")
            else:
                # Поиск файла с правильным базовым именем, но, возможно, другим расширением
                found_path = None
                self.log(f"[DEBUG] Ожидаемый путь к видео '{expected_video_path}' не найден. Поиск в директории '{output_dir}' по шаблону '{context.base}.*'")
                for fname in os.listdir(output_dir):
                    f_base, f_ext = os.path.splitext(fname)
                    if f_base == context.base and f_ext and f_ext.lower() not in [".part", ".ytdl"]:
                        actual_path = os.path.join(output_dir, fname)
                        if os.path.isfile(actual_path):
                             self.log(f"[DEBUG] Найдено возможное совпадение: {actual_path}")
                             found_path = actual_path
                             break

                if found_path:
                     if found_path != expected_video_path:
                        self.log(f"[WARN] Видео скачано как {os.path.basename(found_path)}, ожидалось {os.path.basename(expected_video_path)}. Используется фактический файл.")
                     else:
                         self.log(f"[INFO] Видео успешно скачано: {found_path}")
                     context.video_path = found_path
                else:
                     self.log(f"[ERROR] Ожидаемый видеофайл не найден после скачивания: {expected_video_path} (и альтернативы вида '{context.base}.*' не найдены).")
                     self.log(f"[DEBUG] yt-dlp stdout:\n{process.stdout}")
                     self.log(f"[DEBUG] yt-dlp stderr:\n{process.stderr}")
                     raise FileNotFoundError(f"Ожидаемый видеофайл '{expected_video_path}' или альтернатива не найдены после скачивания.")

        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] yt-dlp завершился с ошибкой при скачивании видео: {e}")
            self.log(f"[ERROR] Команда: {' '.join(e.cmd)}")
            stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
            self.log(f"[ERROR] Stderr: {stderr_output}")
            raise
        except Exception as e:
            self.log(f"[ERROR] Неожиданная ошибка при скачивании видео: {type(e).__name__} - {e}")
            raise