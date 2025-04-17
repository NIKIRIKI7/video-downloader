# File: model/processing_context.py

from dataclasses import dataclass, field
import os
from typing import Optional, List
import constants

@dataclass
class ProcessingContext:
    """Хранит данные и состояние во время обработки видео, включая настройки."""
    # --- Входные данные (Обязательные) ---
    url: str
    output_dir: str

    # --- Входные данные (Опциональные) ---
    yandex_audio: Optional[str] = None # Путь к внешнему аудио

    # --- Настройки (передаются из GUI/ViewModel, с умолчаниями из constants) ---
    source_lang: str = constants.SOURCE_LANG_DEFAULT
    target_lang: str = constants.TARGET_LANG_DEFAULT
    subtitle_lang: str = constants.SUB_LANG_DEFAULT
    subtitle_format: str = constants.SUB_FORMAT_DEFAULT
    video_format_ext: str = constants.VIDEO_FORMAT_EXT_DEFAULT
    yt_dlp_format: str = constants.YT_DLP_FORMAT_DEFAULT
    original_volume: str = constants.ORIGINAL_VOLUME_DEFAULT
    added_volume: str = constants.ADDED_VOLUME_DEFAULT
    merged_audio_codec: str = constants.MERGED_AUDIO_CODEC_DEFAULT

    # --- Данные, получаемые командами (Внутреннее состояние) ---
    base: Optional[str] = None # Базовое имя файла, полученное из ID или заголовка
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    # --- Пути, генерируемые командами (Внутреннее состояние) ---
    video_path: Optional[str] = None
    subtitle_path: Optional[str] = None
    translated_subtitle_path: Optional[str] = None
    metadata_path: Optional[str] = None
    translated_metadata_path: Optional[str] = None
    merged_video_path: Optional[str] = None
    thumbnail_path: Optional[str] = None # Добавлено: Путь к скачанному превью

    def _get_path(self, suffix: str, ext: str) -> Optional[str]:
        """
        Вспомогательный метод для построения полного пути в выходной директории на основе базового имени.
        Обеспечивает согласованное форматирование суффикса и расширения.
        """
        if not self.base:
            return None

        safe_suffix = suffix
        if suffix and not suffix.startswith('.'):
             safe_suffix = f".{suffix}"

        safe_ext = ext.strip()
        if safe_ext and not safe_ext.startswith('.'):
            safe_ext = f".{safe_ext}"
        elif not safe_ext:
             safe_ext = ""

        if safe_suffix.endswith(safe_ext) and safe_ext:
             filename = f"{self.base}{safe_suffix}"
        else:
             filename = f"{self.base}{safe_suffix}{safe_ext}"

        return os.path.join(self.output_dir, filename)

    # --- Методы для получения ожидаемых путей к файлам (используя настройки из контекста) ---

    def get_metadata_filepath(self, lang: Optional[str] = None) -> Optional[str]:
        """Возвращает путь к файлу метаданных."""
        suffix = f".{constants.META_SUFFIX}"
        if lang:
            suffix += f".{lang}"
        return self._get_path(suffix, constants.META_EXT_DEFAULT)

    def get_subtitle_filepath(self, lang: str) -> Optional[str]:
        """Возвращает путь к файлу субтитров для указанного языка."""
        if not lang: return None
        subtitle_ext = self.subtitle_format
        return self._get_path(f".{lang}", subtitle_ext)

    def get_video_filepath(self) -> Optional[str]:
        """Возвращает путь к основному скачанному видеофайлу."""
        video_ext = self.video_format_ext
        return self._get_path("", video_ext) # Нет суффикса для базового видео

    def get_merged_video_filepath(self) -> Optional[str]:
        """Возвращает путь к видеофайлу со смешанным аудио."""
        video_ext = self.video_format_ext
        mix_suffix = f".{constants.AUDIO_MIX_SUFFIX}"
        return self._get_path(mix_suffix, video_ext)

    def get_thumbnail_filepath(self) -> Optional[str]:
        """
        Возвращает путь к файлу превью видео.
        Использует расширение из констант (`constants.THUMBNAIL_EXT_DEFAULT`).
        yt-dlp обычно сохраняет как .jpg, .png или .webp.
        """
        thumb_ext = constants.THUMBNAIL_EXT_DEFAULT
        # yt-dlp добавляет расширение сам, суффикс не нужен.
        return self._get_path("", thumb_ext)