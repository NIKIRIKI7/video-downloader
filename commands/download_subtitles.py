# File: commands/download_subtitles.py

from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
import os

class DownloadSubtitles(ActionCommand):
    """Команда для скачивания субтитров с использованием yt-dlp, на основе настроек контекста."""

    def execute(self, context: ProcessingContext) -> None:
        """Скачивает субтитры на указанном языке и в указанном формате из контекста."""
        if not context.base:
            self.log("[ERROR] Невозможно скачать субтитры: базовое имя файла 'base' не установлено.")
            raise ValueError("Базовое имя файла не установлено в контексте.")

        url = context.url
        output_dir = context.output_dir
        ensure_dir(output_dir)

        lang = context.subtitle_lang
        sub_format = context.subtitle_format

        if not lang:
            self.log("[ERROR] Язык скачивания субтитров не указан в контексте.")
            raise ValueError("Требуется язык скачивания субтитров.")
        if not sub_format:
             self.log("[ERROR] Формат субтитров не указан в контексте.")
             raise ValueError("Требуется формат субтитров.")

        expected_sub_path = context.get_subtitle_filepath(lang)
        if not expected_sub_path:
             self.log("[ERROR] Невозможно определить путь к файлу субтитров.")
             raise ValueError("Не удалось определить путь к файлу субтитров.")

        if os.path.exists(expected_sub_path):
            self.log(f"[WARN] Файл субтитров уже существует: {expected_sub_path}. Пропуск скачивания.")
            context.subtitle_path = expected_sub_path
            return

        yt_dlp_path = get_tool_path('yt-dlp')
        output_template = os.path.join(output_dir, f"{context.base}")

        self.log(f"[INFO] Скачивание субтитров ({lang}, {sub_format})...")
        cmd = [
            yt_dlp_path,
            "--encoding", "utf-8",
            "--no-playlist",
            "--skip-download",
            "--write-sub",
            "--sub-lang", lang,
            "--convert-subs", sub_format,
            "-o", output_template,
            url
        ]

        try:
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

            if os.path.exists(expected_sub_path):
                context.subtitle_path = expected_sub_path
                self.log(f"[INFO] Субтитры успешно скачаны: {expected_sub_path}")
            else:
                alt_sub_path = context._get_path("", sub_format)
                if alt_sub_path and os.path.exists(alt_sub_path):
                    self.log(f"[WARN] Субтитры найдены как {os.path.basename(alt_sub_path)}. Переименование в {os.path.basename(expected_sub_path)}.")
                    try:
                        os.rename(alt_sub_path, expected_sub_path)
                        context.subtitle_path = expected_sub_path
                        self.log(f"[INFO] Субтитры готовы: {expected_sub_path}")
                    except OSError as rename_err:
                         self.log(f"[ERROR] Не удалось переименовать файл субтитров: {rename_err}")
                         context.subtitle_path = alt_sub_path
                else:
                    stderr_lower = process.stderr.lower()
                    no_subs_found = any(msg in stderr_lower for msg in [
                        f"no subtitles found for languages: {lang}",
                        f"unable to download video subtitles for languages: {lang}",
                        "requested format is not available" # More general
                    ])

                    if no_subs_found:
                         self.log(f"[WARN] Субтитры на языке '{lang}' для этого видео недоступны (или формат '{sub_format}' недоступен).")
                    else:
                         self.log(f"[ERROR] Ожидаемый файл субтитров не найден после скачивания: {expected_sub_path}")
                         self.log(f"[DEBUG] yt-dlp stdout:\n{process.stdout}")
                         self.log(f"[DEBUG] yt-dlp stderr:\n{process.stderr}")

        except subprocess.CalledProcessError as e:
            stderr_lower = e.stderr.decode('utf-8', errors='replace').lower() if isinstance(e.stderr, bytes) else e.stderr.lower()
            no_subs_found_err = any(msg in stderr_lower for msg in [
                f"no subtitles found for languages: {lang}",
                f"unable to download video subtitles for languages: {lang}",
                "requested format is not available"
            ])

            if no_subs_found_err:
                 self.log(f"[WARN] Субтитры на языке '{lang}' недоступны (сообщение об ошибке yt-dlp). Формат: '{sub_format}'.")
            else:
                self.log(f"[ERROR] yt-dlp завершился с ошибкой при скачивании субтитров: {e}")
                self.log(f"[ERROR] Команда: {' '.join(e.cmd)}")
                stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
                self.log(f"[ERROR] Stderr: {stderr_output}")
                raise
        except Exception as e:
            self.log(f"[ERROR] Неожиданная ошибка при скачивании субтитров: {type(e).__name__} - {e}")
            raise