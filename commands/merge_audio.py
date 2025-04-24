# File: commands/merge_audio.py

from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import get_tool_path
import subprocess
from pathlib import Path

class MergeAudio(ActionCommand):
    """Команда для слияния аудио дорожки видео с внешним аудио (Yandex) через ffmpeg."""

    def execute(self, context: ProcessingContext) -> None:
        """
        Сливает оригинальную аудио-дорожку видео и внешнюю аудио-дорожку с учётом громкости.
        Результат сохраняется в файл base.mixed.ext.
        """
        video_path: Path = context.video_path  # type: ignore
        yandex_path: Path = context.yandex_audio  # type: ignore
        if not video_path or not video_path.exists():
            raise FileNotFoundError(f"Видеофайл не найден: {video_path}")
        if not yandex_path or not yandex_path.exists():
            raise FileNotFoundError(f"Аудиофайл Yandex не найден: {yandex_path}")
        if not context.base:
            raise ValueError("Не задано базовое имя для слияния аудио.")

        # Парсим громкость
        try:
            vol0 = float(context.original_volume)
            vol1 = float(context.added_volume)
        except ValueError:
            raise ValueError(f"Неправильные значения громкости: {context.original_volume}, {context.added_volume}")

        codec = context.merged_audio_codec
        if not codec:
            raise ValueError("Не задан аудио кодек для слияния.")

        output: Path = context.get_merged_video_filepath()  # type: ignore
        if output and output.exists():
            self.log(f"[WARN] Файл со смешанным аудио уже существует: {output}")
            context.merged_video_path = output
            return

        ffmpeg = get_tool_path('ffmpeg')
        self.log(f"[INFO] Слияние аудио: {video_path.name} + {yandex_path.name} => {output.name}")

        cmd = [
            str(ffmpeg), '-y',
            '-i', str(video_path),
            '-i', str(yandex_path),
            '-filter_complex',
            f"[0:a]volume={vol0}[a0];[1:a]volume={vol1}[a1];[a0][a1]amix=inputs=2:duration=first[aout]",
            '-map', '0:v',
            '-map', '[aout]',
            '-c:v', 'copy',
            '-c:a', codec,
            str(output)
        ]

        try:
            proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
        except subprocess.CalledProcessError as e:
            stderr = e.stderr or ''
            self.log(f"[ERROR] ffmpeg error: {stderr}")
            raise

        if output and output.exists():
            context.merged_video_path = output
            self.log(f"[INFO] Аудио успешно слито: {output}")
        else:
            raise FileNotFoundError(f"Файл не найден после слияния: {output}")
