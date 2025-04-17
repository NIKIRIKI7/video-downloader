from commands.base_command import ActionCommand
from utils import ensure_dir
from constants import VIDEO_DIR
import subprocess
import json
import os
from typing import Dict, Any

class DownloadMetadata(ActionCommand):
    """Команда для загрузки метаданных видео (название, описание, теги) с помощью yt-dlp."""

    def execute(self, context: Dict[str, Any]) -> None:
        """
        Загружает метаданные видео и сохраняет их в файл .meta.txt.
        Также определяет базовое имя файла ('base') для использования другими командами,
        приоритетно используя ID видео.

        Args:
            context: Словарь контекста. Ожидает 'url'.
                     Обновляет 'base', 'title', 'description', 'tags'.

        Raises:
            subprocess.CalledProcessError: Если команда yt-dlp завершилась с ошибкой.
            FileNotFoundError: Если yt-dlp не установлен или не найден в PATH.
            json.JSONDecodeError: Если вывод yt-dlp не является валидным JSON.
            KeyError: Если в контексте отсутствует 'url'.
        """
        url = context['url'] # Может вызвать KeyError, если URL не передан - это ожидаемо
        ensure_dir(VIDEO_DIR) # Убедимся, что директория существует

        self.log(f"Запрос метаданных для URL: {url}")
        try:
            # Используем '-j' для получения JSON вывода
            cmd = ["yt-dlp", "--no-playlist", "--dump-single-json", url]
            result = subprocess.check_output(cmd, text=True, encoding='utf-8')
            data = json.loads(result)

            # Извлечение данных
            video_id = data.get('id', '')
            title = data.get('title', 'untitled')
            description = data.get('description', '')
            tags = data.get('tags', [])

            # Определение базового имени файла
            # Приоритет отдаем ID видео, так как он уникален и не содержит спецсимволов
            base = video_id if video_id else title.replace(' ', '_').replace('/', '_').replace('\\', '_')
            # Дополнительная очистка base от символов, недопустимых в именах файлов
            base = "".join(c for c in base if c.isalnum() or c in ('_', '-')).strip()
            if not base: # Если имя все равно пустое
                base = "video"

            context['base'] = base
            context['title'] = title
            context['description'] = description
            context['tags'] = tags

            meta_path = os.path.join(VIDEO_DIR, f"{base}.meta.txt")
            self.log(f"Сохранение метаданных в: {meta_path}")
            try:
                with open(meta_path, 'w', encoding='utf-8') as f:
                    f.write(f"Title: {title}\n\n")
                    f.write(f"Description:\n{description}\n\n")
                    f.write(f"Tags: {', '.join(tags)}")
                self.log("Метаданные успешно сохранены.")
            except IOError as e:
                self.log(f"Ошибка записи файла метаданных {meta_path}: {e}")
                # Можно решить, прерывать ли выполнение дальше
                # raise # Повторно выбросить исключение, если это критично

        except subprocess.CalledProcessError as e:
            self.log(f"Ошибка выполнения yt-dlp для метаданных: {e}")
            self.log(f"Команда: {' '.join(e.cmd)}")
            self.log(f"Вывод: {e.output}")
            raise # Передаем ошибку выше для обработки
        except FileNotFoundError:
            self.log("Ошибка: команда 'yt-dlp' не найдена. Убедитесь, что yt-dlp установлен и доступен в PATH.")
            raise
        except json.JSONDecodeError as e:
            self.log(f"Ошибка декодирования JSON от yt-dlp: {e}")
            self.log(f"Полученные данные: {result[:500]}...") # Логируем часть данных для отладки
            raise
        except Exception as e:
            self.log(f"Неожиданная ошибка при загрузке метаданных: {e}")
            raise