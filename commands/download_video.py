# File: commands/download_video.py

from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
from pathlib import Path

class DownloadVideo(ActionCommand):
    """Команда для скачивания видео с использованием yt-dlp на основе настроек контекста."""

    def execute(self, context: ProcessingContext) -> None:
        """
        Скачивает видеофайл в формате context.yt_dlp_format и контейнере context.video_format_ext.
        """
        if not context.base:
            self.log("[ERROR] Базовое имя файла не установлено. Пропуск скачивания видео.")
            raise ValueError("Не задано базовое имя для скачивания видео.")

        output_dir: Path = context.output_dir
        ensure_dir(output_dir)

        fmt = context.yt_dlp_format
        ext = context.video_format_ext
        if not fmt:
            raise ValueError("Не указан формат yt-dlp для скачивания видео.")
        if not ext:
            raise ValueError("Не указан расширение выходного видео.")

        expected: Path = context.get_video_filepath()  # type: ignore
        if expected and expected.exists():
            self.log(f"[WARN] Видео уже существует: {expected}")
            context.video_path = expected
            return

        ytdlp = get_tool_path('yt-dlp')
        template = output_dir / f"{context.base}.%(ext)s"
        self.log(f"[INFO] Скачивание видео (формат: '{fmt}', контейнер: '{ext}')...")

        cmd = [
            str(ytdlp),
            '--no-playlist',
            '--format', fmt,
            '--merge-output-format', ext,
            '-o', str(template),
            context.url
        ]

        try:
            proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ''
            self.log(f"[ERROR] yt-dlp error: {stderr}")
            raise

        # Проверяем наличие файла
        if expected and expected.exists():
            context.video_path = expected
            self.log(f"[INFO] Видео сохранено: {expected}")
            return

        # Альтернативный поиск (любое расширение)
        candidates = list(output_dir.glob(f"{context.base}.*"))
        for file in candidates:
            if file.suffix not in ['.part', '']:
                context.video_path = file
                self.log(f"[WARN] Найдено видео как {file.name}, используем этот файл.")
                return

        self.log(f"[ERROR] Ожидаемый видеофайл не найден: {expected}")
        raise FileNotFoundError(f"Видео не найдено после загрузки: {expected}")
