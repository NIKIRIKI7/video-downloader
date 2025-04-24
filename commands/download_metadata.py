# File: commands/download_metadata.py

from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
import json
from pathlib import Path

class DownloadMetadata(ActionCommand):
    """Команда для скачивания метаданных видео с использованием yt-dlp."""

    def execute(self, context: ProcessingContext) -> None:
        """
        Скачивает метаданные, сохраняет их и заполняет context.base, title и другие поля.
        """
        url = context.url
        output_dir = context.output_dir
        ensure_dir(output_dir)

        self.log("[INFO] Запрос метаданных...")
        yt_dlp_path = get_tool_path('yt-dlp')

        try:
            cmd = [str(yt_dlp_path), "--no-playlist", "--dump-single-json", "--skip-download", url]
            result = subprocess.check_output(cmd, text=True, encoding='utf-8', stderr=subprocess.PIPE)
            data = json.loads(result)

            video_id = data.get('id', '')
            title = data.get('title', 'untitled')
            description = data.get('description', '')
            tags = data.get('tags', []) or []

            # Формируем безопасное базовое имя
            raw_base = video_id or title
            safe = ''.join(c if c.isalnum() or c in (' ', '-', '_') else '_' for c in raw_base)
            safe = '_'.join(safe.split())[:100] or 'video'
            context.base = safe
            context.title = title
            context.description = description
            context.tags = tags

            # Сохранение оригинального мета-файла
            meta_path = context.get_metadata_filepath(lang=None)
            if not meta_path:
                raise ValueError("Невозможно определить путь к файлу метаданных.")
            context.metadata_path = meta_path
            self.log(f"[INFO] Сохранение метаданных: {meta_path}")
            with open(meta_path, 'w', encoding='utf-8') as f:
                f.write(f"ID: {video_id}\n")
                f.write(f"Title: {title}\n\n")
                f.write(f"Description:\n{description}\n\n")
                f.write(f"Tags: {', '.join(tags)}")
            self.log("[INFO] Метаданные сохранены.")

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
            self.log(f"[ERROR] yt-dlp error: {stderr}")
            raise
        except json.JSONDecodeError as e:
            self.log(f"[ERROR] Ошибка парсинга JSON: {e}")
            raise
        except Exception as e:
            self.log(f"[ERROR] Неожиданная ошибка: {type(e).__name__} - {e}")
            raise
