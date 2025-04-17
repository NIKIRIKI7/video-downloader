from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import get_tool_path
import subprocess
import os

class MergeAudio(ActionCommand):
    """Команда для слияния аудио видео с внешним аудиофайлом с помощью ffmpeg, на основе настроек контекста."""

    def execute(self, context: ProcessingContext) -> None:
        """Сливает аудио видео с аудиофайлом Yandex, используя настройки громкости/кодека из контекста."""
        if not context.video_path:
            self.log("[ERROR] Невозможно слить аудио: Путь к видео не найден в контексте (действие 'Скачать видео' было выполнено успешно?).")
            raise ValueError("Путь к видео отсутствует в контексте для слияния аудио.")
        if not context.yandex_audio:
            self.log("[ERROR] Невозможно слить аудио: Путь к аудио Yandex не предоставлен в контексте.")
            raise ValueError("Путь к аудио Yandex отсутствует в контексте для слияния аудио.")
        if not context.base:
            self.log("[ERROR] Невозможно слить аудио: Базовое имя файла не установлено в контексте.")
            raise ValueError("Базовое имя файла не установлено в контексте для слияния аудио.")

        video_path = context.video_path
        yandex_audio_path = context.yandex_audio

        try:
            original_volume_float = float(context.original_volume)
            added_volume_float = float(context.added_volume)
            original_volume = context.original_volume
            added_volume = context.added_volume
        except ValueError:
            self.log(f"[ERROR] Найдены неверные настройки громкости: Оригинал='{context.original_volume}', Добавленное='{context.added_volume}'. Должны быть числами.")
            raise ValueError("Предоставлены неверные настройки громкости.")

        merged_audio_codec = context.merged_audio_codec
        if not merged_audio_codec:
            self.log("[ERROR] Аудио кодек для слияния не указан в контексте.")
            raise ValueError("Требуется аудио кодек для слияния.")

        output_path = context.get_merged_video_filepath()
        if not output_path:
            self.log("[ERROR] Невозможно определить путь для выходного видео со слиянием.")
            raise ValueError("Не удалось определить путь для выходного видео со слиянием.")

        if not os.path.exists(video_path):
            self.log(f"[ERROR] Слияние аудио не удалось: Входной видеофайл не найден: {video_path}")
            raise FileNotFoundError(f"Входной видеофайл не найден: {video_path}")
        if not os.path.exists(yandex_audio_path):
            self.log(f"[ERROR] Слияние аудио не удалось: Аудиофайл Yandex не найден: {yandex_audio_path}")
            raise FileNotFoundError(f"Аудиофайл Yandex не найден: {yandex_audio_path}")

        if os.path.exists(output_path):
             self.log(f"[WARN] Видеофайл со слиянием уже существует: {output_path}. Пропуск слияния.")
             context.merged_video_path = output_path
             return

        ffmpeg_path = get_tool_path('ffmpeg')

        self.log(f"[INFO] Слияние аудиодорожек в: {output_path}")
        self.log(f"[DEBUG] Входное видео: {video_path}")
        self.log(f"[DEBUG] Входное аудио: {yandex_audio_path}")
        self.log(f"[DEBUG] Громкость оригинала: {original_volume}")
        self.log(f"[DEBUG] Громкость добавленного: {added_volume}")
        self.log(f"[DEBUG] Выходной кодек: {merged_audio_codec}")

        cmd = [
            ffmpeg_path, "-y",
            "-i", video_path,
            "-i", yandex_audio_path,
            "-filter_complex",
                f"[0:a]volume={original_volume}[a0];"
                f"[1:a]volume={added_volume}[a1];"
                f"[a0][a1]amix=inputs=2:duration=first[aout]",
            "-map", "0:v",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", merged_audio_codec,
            output_path
        ]
        self.log(f"[DEBUG] Выполнение команды FFmpeg: {' '.join(cmd)}")

        try:
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')

            if os.path.exists(output_path):
                context.merged_video_path = output_path
                self.log(f"[INFO] Аудио успешно слито: {output_path}")
                self.log(f"[INFO] >>> Финальное видео со смешанным аудио: {output_path} <<<")
            else:
                self.log(f"[ERROR] Видеофайл со слиянием не найден после успешной команды ffmpeg: {output_path}")
                self.log(f"[DEBUG] ffmpeg stdout:\n{process.stdout}")
                self.log(f"[DEBUG] ffmpeg stderr:\n{process.stderr}")
                raise FileNotFoundError(f"Видеофайл со слиянием не найден, несмотря на успешное выполнение ffmpeg: {output_path}")

        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] ffmpeg завершился с ошибкой во время слияния аудио: {e}")
            self.log(f"[ERROR] Команда: {' '.join(cmd)}")
            stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
            self.log(f"[ERROR] Stderr: {stderr_output}")
            raise
        except Exception as e:
            self.log(f"[ERROR] Неожиданная ошибка во время слияния аудио: {type(e).__name__} - {e}")
            raise