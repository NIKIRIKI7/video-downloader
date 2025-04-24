# File: commands/download_thumbnail.py

from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
from pathlib import Path

class DownloadThumbnail(ActionCommand):  # наследуем от ActionCommand
    """Команда для скачивания превью видео с использованием yt-dlp."""

    def execute(self, context: ProcessingContext) -> None:
        """
        Скачивает файл превью (thumbnail) для видео.
        """
        if not context.base:
            self.log("[ERROR] Базовое имя файла не установлено. Пропуск скачивания превью.")
            raise ValueError("Не задано базовое имя для скачивания превью.")

        output_dir: Path = context.output_dir
        ensure_dir(output_dir)

        ytdlp = get_tool_path('yt-dlp')
        expected_default: Path = context.get_thumbnail_filepath()  # type: ignore

        # Если уже скачано с одним из популярных расширений
        if expected_default and expected_default.exists():
            context.thumbnail_path = expected_default
            self.log(f"[WARN] Превью уже существует: {expected_default}")
            return

        # Команда yt-dlp для скачивания превью
        cmd = [
            str(ytdlp),
            '--no-playlist',
            '--skip-download',
            '--write-thumbnail',
            '--paths', str(output_dir),
            context.url
        ]
        self.log("[INFO] Скачивание превью видео...")

        try:
            proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ''
            if 'no thumbnails found' in stderr.lower() or 'unable to download thumbnail' in stderr.lower():
                self.log("[WARN] Превью недоступно для данного видео.")
                return
            self.log(f"[ERROR] yt-dlp error при скачивании превью: {stderr}")
            raise

        # Пытаемся найти файл в output_dir
        for ext in ['.jpg', '.jpeg', '.png', '.webp']:
            candidate = output_dir / f"{context.base}{ext}"
            if candidate.exists():
                context.thumbnail_path = candidate
                self.log(f"[INFO] Превью сохранено: {candidate}")
                return

        # Альтернативный поиск по любому расширению
        matches = list(output_dir.glob(f"{context.base}.*"))
        for m in matches:
            if m.is_file() and m.suffix.lower() in ['.jpg', '.jpeg', '.png', '.webp']:
                context.thumbnail_path = m
                self.log(f"[INFO] Превью найдено как {m.name}")
                return

        self.log("[WARN] Не удалось найти файл превью после выполнения команды.")
