# File: commands/download_subtitles.py

from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
from pathlib import Path

class DownloadSubtitles(ActionCommand):
    """Команда для скачивания субтитров с использованием yt-dlp на основе настроек контекста."""

    def execute(self, context: ProcessingContext) -> None:
        """
        Скачивает субтитры в формате и языке, указанных в контексте.
        """
        if not context.base:
            self.log("[ERROR] Базовое имя файла не установлено. Пропуск субтитров.")
            raise ValueError("Не задано базовое имя для скачивания субтитров.")

        output_dir: Path = context.output_dir
        ensure_dir(output_dir)

        lang = context.subtitle_lang
        fmt = context.subtitle_format
        if not lang:
            raise ValueError("Не указан язык субтитров.")
        if not fmt:
            raise ValueError("Не указан формат субтитров.")

        expected_path: Path = context.get_subtitle_filepath(lang)  # type: ignore
        if expected_path and expected_path.exists():
            self.log(f"[WARN] Субтитры уже существуют: {expected_path}")
            context.subtitle_path = expected_path
            return

        yt_dlp = get_tool_path('yt-dlp')
        self.log(f"[INFO] Скачивание субтитров ({lang}, {fmt})...")

        cmd = [
            str(yt_dlp),
            '--no-playlist',
            '--skip-download',
            '--write-sub',
            '--sub-lang', lang,
            '--convert-subs', fmt,
            '-o', str(output_dir / f"{context.base}.%(ext)s"),
            context.url
        ]

        try:
            proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ''
            if 'unable to download subtitle' in stderr.lower() or 'no subtitles found' in stderr.lower():
                self.log(f"[WARN] Субтитры для языка '{lang}' недоступны.")
                return
            self.log(f"[ERROR] Ошибка yt-dlp при скачивании субтитров: {stderr}")
            raise

        # После выполнения пытаемся найти файл
        if expected_path and expected_path.exists():
            context.subtitle_path = expected_path
            self.log(f"[INFO] Субтитры сохранены: {expected_path}")
            return

        # Альтернативный поиск по шаблону
        matched = list(output_dir.glob(f"{context.base}*.{fmt}"))
        if matched:
            result = matched[0]
            # Попытка переименования
            if expected_path:
                result.rename(expected_path)
                context.subtitle_path = expected_path
                self.log(f"[INFO] Субтитры переименованы в: {expected_path}")
            else:
                context.subtitle_path = result
                self.log(f"[INFO] Субтитры сохранены как: {result}")
        else:
            self.log(f"[WARN] Не удалось найти файл субтитров после выполнения команды.")
