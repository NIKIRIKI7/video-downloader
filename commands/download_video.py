from commands.base_command import ActionCommand
from utils import ensure_dir
from constants import VIDEO_DIR
import subprocess
import os
from typing import Dict, Any

class DownloadVideo(ActionCommand):
    """Команда для загрузки видео (и аудио) в формате MP4 с помощью yt-dlp."""

    VIDEO_FORMAT = "mp4"
    # Опции yt-dlp: лучшее видео + лучшее аудио, объединить в mp4
    YT_DLP_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"

    def execute(self, context: Dict[str, Any]) -> None:
        """
        Загружает видеофайл для указанного URL.

        Args:
            context: Словарь контекста. Ожидает 'url' и 'base'.
                     Обновляет 'video_path'.

        Raises:
            subprocess.CalledProcessError: Если команда yt-dlp завершилась с ошибкой.
            FileNotFoundError: Если yt-dlp не установлен или не найден в PATH,
                               или если ожидаемый видеофайл не был создан.
            KeyError: Если в контексте отсутствуют 'url' или 'base'.
        """
        url = context['url']
        base = context['base'] # Ожидаем, что 'base' установлен DownloadMetadata
        ensure_dir(VIDEO_DIR)

        # Формируем ожидаемый путь к видеофайлу
        expected_video_filename = f"{base}.{self.VIDEO_FORMAT}"
        expected_video_path = os.path.join(VIDEO_DIR, expected_video_filename)
        context['video_path'] = expected_video_path # Записываем ожидаемый путь в контекст

        # Формируем шаблон для yt-dlp
        output_template = os.path.join(VIDEO_DIR, f"{base}.%(ext)s")

        self.log(f"Загрузка видео в формате {self.VIDEO_FORMAT} для URL: {url}")
        # Команда yt-dlp
        # Замечание: --write-description и --write-sub могут быть избыточны,
        # если используются команды DownloadMetadata и DownloadSubtitles.
        # Пока оставляем для универсальности, если эта команда используется отдельно.
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--format", self.YT_DLP_FORMAT,
            "--merge-output-format", self.VIDEO_FORMAT,
            # "--write-description", # Можно убрать, если есть DownloadMetadata
            # "--write-sub", "--sub-lang", "en", "--convert-subs", "vtt", # Можно убрать, если есть DownloadSubtitles
            "-o", output_template,
            url
        ]

        try:
            # Запускаем yt-dlp
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            self.log(f"yt-dlp вывод (видео):\n{process.stdout}\n{process.stderr}")

            # Проверяем, был ли создан ожидаемый видеофайл
            if os.path.exists(expected_video_path):
                self.log(f"Видео успешно загружено: {expected_video_path}")
            else:
                # Проверим, не скачался ли файл с другим расширением (например, webm)
                found_video = None
                for fname in os.listdir(VIDEO_DIR):
                    f_base, f_ext = os.path.splitext(fname)
                    # Ищем файл с тем же 'base', но другим контейнером
                    if f_base == base and f_ext != f".{self.VIDEO_FORMAT}" and f_ext in ['.mkv', '.webm', '.avi']:
                        found_video = os.path.join(VIDEO_DIR, fname)
                        self.log(f"Предупреждение: Видео скачано как {fname}. Путь в контексте остается {expected_video_path}.")
                        # Можно добавить перекодирование в mp4 здесь, если это необходимо
                        # Но пока просто сообщаем и используем то, что есть, если ffmpeg потом справится
                        context['video_path'] = found_video # Обновляем путь в контексте на фактический
                        break
                if not found_video:
                     self.log(f"Ошибка: Ожидаемый видеофайл не найден: {expected_video_path}")
                     raise FileNotFoundError(f"Ожидаемый видеофайл не найден: {expected_video_path}")

        except subprocess.CalledProcessError as e:
            self.log(f"Ошибка выполнения yt-dlp для видео: {e}")
            self.log(f"Команда: {' '.join(e.cmd)}")
            self.log(f"Вывод: {e.stderr}") # Ошибки часто в stderr
            raise # Передаем ошибку выше
        except FileNotFoundError:
            # Может быть FileNotFoundError и если yt-dlp не найден
            self.log("Ошибка: команда 'yt-dlp' не найдена или не удалось создать видеофайл. Убедитесь, что yt-dlp установлен и доступен в PATH.")
            raise
        except Exception as e:
            self.log(f"Неожиданная ошибка при загрузке видео: {e}")
            raise