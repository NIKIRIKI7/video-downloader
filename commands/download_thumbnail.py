from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
import os

class DownloadThumbnail(ActionCommand):
    """Команда для скачивания превью видео с использованием yt-dlp."""

    def execute(self, context: ProcessingContext) -> None:
        """Скачивает файл превью."""
        if not context.base:
            self.log("[ERROR] Невозможно скачать превью: базовое имя файла 'base' не установлено в контексте.")
            raise ValueError("Базовое имя файла не установлено в контексте перед скачиванием превью.")

        url = context.url
        output_dir = context.output_dir
        ensure_dir(output_dir)

        # yt-dlp сам определит лучшее расширение (jpg, webp, png)
        # Мы используем get_thumbnail_filepath для *проверки* результата,
        # но yt-dlp определит фактическое имя.
        # Базовый шаблон вывода для yt-dlp
        output_template = os.path.join(output_dir, f"{context.base}.%(ext)s")
        # Ожидаемый путь с расширением по умолчанию для проверки
        expected_thumb_path_default = context.get_thumbnail_filepath()

        if not expected_thumb_path_default:
             self.log("[ERROR] Невозможно определить ожидаемый путь к файлу превью.")
             raise ValueError("Не удалось определить ожидаемый путь к файлу превью.")

        # Проверим, существует ли уже превью с одним из стандартных расширений
        possible_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        existing_thumb = None
        for ext in possible_extensions:
            potential_path = os.path.join(output_dir, context.base + ext)
            if os.path.exists(potential_path):
                existing_thumb = potential_path
                break

        if existing_thumb:
             self.log(f"[WARN] Файл превью уже существует: {existing_thumb}. Пропуск скачивания.")
             context.thumbnail_path = existing_thumb # Сохраняем путь к существующему
             return

        yt_dlp_path = get_tool_path('yt-dlp')

        self.log(f"[INFO] Скачивание превью видео...")
        cmd = [
            yt_dlp_path,
            "--encoding", "utf-8",
            "--no-playlist",
            "--skip-download",      # Не скачивать видео/аудио
            "--write-thumbnail",    # Скачать превью
            # "-o", output_template # Не указываем шаблон имени для превью, yt-dlp сам его назовет по ID или заголовку
                                    # Указываем output_dir через -P или --paths
            "--paths", output_dir,  # Указать директорию вывода
             # yt-dlp > 2023.07.06 использует --output вместо -o для превью, но --paths работает для директории
             # Если старая версия: "-o", os.path.join(output_dir, f"{context.base}.%(thumbnail_ext)s"),
            url
        ]
        self.log(f"[DEBUG] Выполнение команды yt-dlp: {' '.join(cmd)}")

        try:
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            # self.log(f"[DEBUG] yt-dlp stdout (thumbnail):\n{process.stdout}")
            # self.log(f"[DEBUG] yt-dlp stderr (thumbnail):\n{process.stderr}")

            # После выполнения команды, ищем скачанный файл
            downloaded_thumb = None
            for ext in possible_extensions:
                potential_path = os.path.join(output_dir, context.base + ext)
                if os.path.exists(potential_path):
                    downloaded_thumb = potential_path
                    break

            if downloaded_thumb:
                context.thumbnail_path = downloaded_thumb
                self.log(f"[INFO] Превью успешно скачано: {downloaded_thumb}")
            else:
                # Проверить stderr на случай, если превью не было найдено
                stderr_lower = process.stderr.lower()
                if "unable to download thumbnail" in stderr_lower or "no thumbnails found" in stderr_lower:
                    self.log("[WARN] Не удалось скачать превью (возможно, оно отсутствует у видео).")
                else:
                    self.log(f"[ERROR] Файл превью не найден после выполнения команды yt-dlp (ожидался файл вида {context.base}.[jpg|png|webp]).")
                    self.log(f"[DEBUG] yt-dlp stdout:\n{process.stdout}")
                    self.log(f"[DEBUG] yt-dlp stderr:\n{process.stderr}")
                    # Не поднимаем ошибку, так как превью может быть опциональным

        except subprocess.CalledProcessError as e:
             # Проверить stderr на случай, если ошибка связана с отсутствием превью
            stderr_lower = e.stderr.decode('utf-8', errors='replace').lower() if isinstance(e.stderr, bytes) else e.stderr.lower()
            if "unable to download thumbnail" in stderr_lower or "no thumbnails found" in stderr_lower:
                self.log("[WARN] Не удалось скачать превью (сообщение об ошибке yt-dlp, возможно, оно отсутствует).")
            else:
                self.log(f"[ERROR] yt-dlp завершился с ошибкой при скачивании превью: {e}")
                self.log(f"[ERROR] Команда: {' '.join(e.cmd)}")
                stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
                self.log(f"[ERROR] Stderr: {stderr_output}")
                # Не перевыбрасываем ошибку, если превью считается некритичным
                # raise
        except Exception as e:
            self.log(f"[ERROR] Неожиданная ошибка при скачивании превью: {type(e).__name__} - {e}")
            raise # Перевыбрасываем неожиданные ошибки