from commands.base_command import ActionCommand
from constants import VIDEO_DIR
import subprocess
import os
from typing import Dict, Any

class MergeAudio(ActionCommand):
    """Команда для слияния оригинальной аудиодорожки видео с предоставленным аудиофайлом (Yandex) с помощью ffmpeg."""

    OUTPUT_SUFFIX = ".mixed"
    # Параметры громкости: оригинальная тише (0.7), добавленная громче (1.0)
    # Можно вынести в параметры или константы
    ORIGINAL_VOLUME = "0.7"
    ADDED_VOLUME = "1.0"

    def execute(self, context: Dict[str, Any]) -> None:
        """
        Сливает аудиодорожку из context['video_path'] с аудиофайлом context['yandex_audio'].

        Args:
            context: Словарь контекста. Ожидает 'base', 'video_path', 'yandex_audio'.
                     Обновляет 'merged_video_path'.

        Raises:
            KeyError: Если в контексте отсутствуют необходимые ключи.
            FileNotFoundError: Если ffmpeg не найден, или если входные видео/аудио файлы не существуют.
            subprocess.CalledProcessError: Если команда ffmpeg завершилась с ошибкой.
        """
        if 'video_path' not in context or not context['video_path']:
            self.log("Пропуск слияния аудио: путь к видеофайлу не найден в контексте.")
            return
        if 'yandex_audio' not in context or not context['yandex_audio']:
            self.log("Пропуск слияния аудио: путь к аудиофайлу Yandex не найден в контексте.")
            return
        if 'base' not in context:
             self.log("Пропуск слияния аудио: базовое имя файла ('base') не найдено в контексте.")
             return

        base = context['base']
        video_path = context['video_path']
        yandex_audio_path = context['yandex_audio']

        # Проверка существования входных файлов
        if not os.path.exists(video_path):
            self.log(f"Ошибка слияния: Видеофайл не найден: {video_path}")
            raise FileNotFoundError(f"Видеофайл не найден: {video_path}")
        if not os.path.exists(yandex_audio_path):
            self.log(f"Ошибка слияния: Аудиофайл Yandex не найден: {yandex_audio_path}")
            raise FileNotFoundError(f"Аудиофайл Yandex не найден: {yandex_audio_path}")

        # Определение имени выходного файла
        video_dir, video_filename = os.path.split(video_path)
        video_name, video_ext = os.path.splitext(video_filename)
        # Используем base для большей надежности, если имя видеофайла отличается
        output_filename = f"{base}{self.OUTPUT_SUFFIX}{video_ext if video_ext else '.mp4'}" # Добавляем расширение, если его нет
        output_path = os.path.join(video_dir, output_filename) # Сохраняем в той же директории

        self.log(f"Слияние аудио из {video_path} и {yandex_audio_path} в {output_path}")

        # Команда ffmpeg
        cmd = [
            "ffmpeg",
            "-y",  # Перезаписывать выходной файл без запроса
            "-i", video_path,          # Входное видео (источник видео и оригинального аудио)
            "-i", yandex_audio_path,   # Входное аудио (добавляемое)
            "-filter_complex",       # Использование сложного фильтра для микширования
                # [0:a] - аудиодорожка из первого входа (видео)
                # [1:a] - аудиодорожка из второго входа (Yandex)
                # volume=... - установка громкости
                # amix - фильтр микширования
                # inputs=2 - два входа
                # duration=first - длительность определяется первым входом (видео)
                # [aout] - имя выходного аудиопотока
                f"[0:a]volume={self.ORIGINAL_VOLUME}[a0];[1:a]volume={self.ADDED_VOLUME}[a1];[a0][a1]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",      # Взять видеодорожку из первого входа (0:v)
            "-map", "[aout]",   # Взять смикшированную аудиодорожку ([aout])
            "-c:v", "copy",     # Копировать видеокодек (быстро, без перекодирования)
            "-c:a", "aac",      # Кодировать итоговое аудио в AAC (широко совместимый кодек)
            # Можно добавить битрейт аудио: "-b:a", "192k"
            output_path
        ]

        try:
            # Запускаем ffmpeg
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            # ffmpeg часто пишет много информации в stderr, даже при успехе
            self.log(f"ffmpeg вывод:\n{process.stdout}\n{process.stderr}")

            # Проверяем, создался ли выходной файл
            if os.path.exists(output_path):
                context['merged_video_path'] = output_path
                self.log(f"Аудио успешно слито: {output_path}")
            else:
                self.log(f"Ошибка: Выходной файл после слияния аудио не найден: {output_path}")
                # Возможно, ffmpeg завершился без ошибки, но файл не создал? Маловероятно, но проверим.
                raise FileNotFoundError(f"Выходной файл после слияния аудио не найден: {output_path}")

        except subprocess.CalledProcessError as e:
            self.log(f"Ошибка выполнения ffmpeg для слияния аудио: {e}")
            self.log(f"Команда: {' '.join(e.cmd)}")
            self.log(f"Вывод stderr:\n{e.stderr}") # Ошибки ffmpeg обычно в stderr
            raise # Передаем ошибку выше
        except FileNotFoundError:
            # Может быть FileNotFoundError и если ffmpeg не найден
            self.log("Ошибка: команда 'ffmpeg' не найдена. Убедитесь, что ffmpeg установлен и доступен в PATH.")
            raise
        except Exception as e:
            self.log(f"Неожиданная ошибка при слиянии аудио: {e}")
            raise