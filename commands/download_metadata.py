# File: commands/download_metadata.py

from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
import json
import os
import re # For cleaning filenames

class DownloadMetadata(ActionCommand):
    """Команда для скачивания метаданных видео с использованием yt-dlp."""

    def execute(self, context: ProcessingContext) -> None:
        """
        Скачивает метаданные, сохраняет их и заполняет context.base, title и т.д.
        """
        url = context.url
        output_dir = context.output_dir
        ensure_dir(output_dir)

        self.log("[INFO] Запрос метаданных...")
        yt_dlp_path = get_tool_path('yt-dlp') # Вызовет FileNotFoundError, если не найден

        try:
            cmd = [yt_dlp_path, "--no-playlist", "--dump-single-json", "--skip-download", url]
            result = subprocess.check_output(cmd, text=True, encoding='utf-8', stderr=subprocess.PIPE)
            data = json.loads(result)

            video_id = data.get('id', '')
            title = data.get('title', 'untitled')
            description = data.get('description', '')
            tags = data.get('tags', [])

            # --- Определение базового имени файла (приоритет у ID) ---
            raw_base = video_id if video_id else title
            safe_base = re.sub(r'[<>:"/\\|?*]', '_', raw_base)
            safe_base = re.sub(r'\s+', '_', safe_base)
            safe_base = safe_base[:100]
            if not safe_base:
                safe_base = "video"
            context.base = safe_base
            # ---

            context.title = title
            context.description = description
            context.tags = tags

            # Сохранение метаданных в файл
            meta_path = context.get_metadata_filepath(lang=None)
            if not meta_path:
                 self.log("[ERROR] Невозможно определить путь к файлу метаданных (отсутствует базовое имя?).")
                 raise ValueError("Не удалось определить путь к файлу метаданных (отсутствует базовое имя).")

            context.metadata_path = meta_path
            self.log(f"[INFO] Сохранение метаданных в: {meta_path}")
            try:
                with open(meta_path, 'w', encoding='utf-8') as f:
                    f.write(f"ID: {video_id}\n")
                    f.write(f"Title: {title}\n\n")
                    f.write(f"Description:\n{description}\n\n")
                    f.write(f"Tags: {', '.join(tags)}")
                self.log("[INFO] Метаданные успешно сохранены.")
            except IOError as e:
                self.log(f"[ERROR] Не удалось записать файл метаданных {meta_path}: {e}")
                raise

        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] yt-dlp завершился с ошибкой при получении метаданных: {e}")
            self.log(f"[ERROR] Команда: {' '.join(e.cmd)}")
            stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
            self.log(f"[ERROR] Stderr: {stderr_output}")
            raise
        except json.JSONDecodeError as e:
            self.log(f"[ERROR] Не удалось декодировать JSON из yt-dlp: {e}")
            log_data = result[:500] if 'result' in locals() else "N/A"
            self.log(f"[DEBUG] Полученные данные (частично): {log_data}...")
            raise
        except Exception as e:
            self.log(f"[ERROR] Неожиданная ошибка при скачивании метаданных: {type(e).__name__} - {e}")
            raise