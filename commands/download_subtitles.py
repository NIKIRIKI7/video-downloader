from commands.base_command import ActionCommand
from utils import ensure_dir
from constants import VIDEO_DIR
import subprocess
import os
from typing import Dict, Any

class DownloadSubtitles(ActionCommand):
    """Команда для загрузки английских субтитров видео в формате VTT с помощью yt-dlp."""

    SUB_LANG = "en"
    SUB_FORMAT = "vtt"

    def execute(self, context: Dict[str, Any]) -> None:
        """
        Загружает субтитры для указанного URL.

        Args:
            context: Словарь контекста. Ожидает 'url' и 'base'.
                     Обновляет 'subtitle_path' (путь к загруженным субтитрам).

        Raises:
            subprocess.CalledProcessError: Если команда yt-dlp завершилась с ошибкой.
            FileNotFoundError: Если yt-dlp не установлен или не найден в PATH,
                               или если ожидаемый файл субтитров не был создан.
            KeyError: Если в контексте отсутствуют 'url' или 'base'.
        """
        url = context['url']
        base = context['base'] # Ожидаем, что 'base' установлен предыдущей командой (DownloadMetadata)
        ensure_dir(VIDEO_DIR)

        # Формируем ожидаемое имя файла субтитров
        # yt-dlp по умолчанию добавляет язык к имени, если base не содержит его
        # Формат имени: {base}.{lang}.{ext}
        expected_sub_filename = f"{base}.{self.SUB_LANG}.{self.SUB_FORMAT}"
        expected_sub_path = os.path.join(VIDEO_DIR, expected_sub_filename)

        # Формируем шаблон для yt-dlp, чтобы он создал файл с нужным именем
        # Важно: Указываем только имя без расширения, yt-dlp добавит язык и расширение сам
        output_template = os.path.join(VIDEO_DIR, f"{base}.%(ext)s")

        self.log(f"Загрузка субтитров ({self.SUB_LANG}, {self.SUB_FORMAT}) для URL: {url}")
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--skip-download", # Только субтитры
            "--write-sub",
            "--sub-lang", self.SUB_LANG,
            "--convert-subs", self.SUB_FORMAT,
            "-o", output_template, # Шаблон имени выходного файла (без субтитров)
            url
        ]

        try:
            # Запускаем yt-dlp
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            self.log(f"yt-dlp вывод (субтитры):\n{process.stdout}\n{process.stderr}")

            # Проверяем, был ли создан ожидаемый файл
            if os.path.exists(expected_sub_path):
                context['subtitle_path'] = expected_sub_path
                self.log(f"Субтитры успешно загружены: {expected_sub_path}")
            else:
                # Попробуем найти файл с немного другим именем (иногда yt-dlp может не добавить язык, если он один)
                alt_sub_filename = f"{base}.{self.SUB_FORMAT}"
                alt_sub_path = os.path.join(VIDEO_DIR, alt_sub_filename)
                if os.path.exists(alt_sub_path):
                     # Переименуем для консистентности
                     os.rename(alt_sub_path, expected_sub_path)
                     context['subtitle_path'] = expected_sub_path
                     self.log(f"Субтитры найдены как {alt_sub_filename}, переименованы в {expected_sub_filename}")
                else:
                    self.log(f"Ошибка: Ожидаемый файл субтитров не найден: {expected_sub_path}")
                    self.log(f"Возможно, субтитры на языке '{self.SUB_LANG}' отсутствуют для этого видео.")
                    # Не выбрасываем ошибку, но и не устанавливаем 'subtitle_path'
                    # Следующие шаги (перевод) должны это проверить
                    # raise FileNotFoundError(f"Ожидаемый файл субтитров не найден: {expected_sub_path}")

        except subprocess.CalledProcessError as e:
            self.log(f"Ошибка выполнения yt-dlp для субтитров: {e}")
            self.log(f"Команда: {' '.join(e.cmd)}")
            self.log(f"Вывод: {e.stderr}") # Ошибки часто в stderr
            # Проверим stderr на сообщение о недоступности субтитров
            if f"subtitles for {self.SUB_LANG}" in e.stderr:
                 self.log(f"Субтитры на языке '{self.SUB_LANG}' недоступны.")
                 # Не считаем это критической ошибкой, просто пропускаем шаг
            else:
                 raise # Передаем другие ошибки выше
        except FileNotFoundError:
            self.log("Ошибка: команда 'yt-dlp' не найдена. Убедитесь, что yt-dlp установлен и доступен в PATH.")
            raise
        except Exception as e:
            self.log(f"Неожиданная ошибка при загрузке субтитров: {e}")
            raise