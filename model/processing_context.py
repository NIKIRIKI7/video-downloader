from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, List
import constants

@dataclass
class ProcessingContext:
    """Контекст обработки видео, хранит входные данные, настройки и пути результатов."""
    url: str
    output_dir: Path

    yandex_audio: Optional[Path] = None

    source_lang: str = constants.SOURCE_LANG_DEFAULT
    target_lang: str = constants.TARGET_LANG_DEFAULT
    subtitle_lang: str = constants.SUB_LANG_DEFAULT
    subtitle_format: str = constants.SUB_FORMAT_DEFAULT
    video_format_ext: str = constants.VIDEO_FORMAT_EXT_DEFAULT
    yt_dlp_format: str = constants.YT_DLP_FORMAT_DEFAULT
    original_volume: str = constants.ORIGINAL_VOLUME_DEFAULT
    added_volume: str = constants.ADDED_VOLUME_DEFAULT
    merged_audio_codec: str = constants.MERGED_AUDIO_CODEC_DEFAULT

    base: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)

    video_path: Optional[Path] = None
    subtitle_path: Optional[Path] = None
    translated_subtitle_path: Optional[Path] = None
    metadata_path: Optional[Path] = None
    translated_metadata_path: Optional[Path] = None
    merged_video_path: Optional[Path] = None
    thumbnail_path: Optional[Path] = None

    def _get_path(self, suffix: str, ext: str) -> Optional[Path]:
        if not self.base:
            return None
        # Подготовка суффикса и расширения
        suffix_clean = suffix if suffix.startswith('.') or not suffix else f".{suffix.lstrip('.')}"
        ext_clean = ext if ext.startswith('.') or not ext else f".{ext.lstrip('.')}"
        filename = (
            f"{self.base}{suffix_clean}{ext_clean}" 
            if not suffix_clean.endswith(ext_clean) 
            else f"{self.base}{suffix_clean}"
        )
        return self.output_dir / filename

    def get_metadata_filepath(self, lang: Optional[str] = None) -> Optional[Path]:
        suffix = f".{constants.META_SUFFIX}"
        if lang:
            suffix += f".{lang}"
        return self._get_path(suffix, constants.META_EXT_DEFAULT)

    def get_subtitle_filepath(self, lang: str) -> Optional[Path]:
        if not lang:
            return None
        return self._get_path(f".{lang}", self.subtitle_format)

    def get_video_filepath(self) -> Optional[Path]:
        return self._get_path("", self.video_format_ext)

    def get_merged_video_filepath(self) -> Optional[Path]:
        return self._get_path(f".{constants.AUDIO_MIX_SUFFIX}", self.video_format_ext)

    def get_thumbnail_filepath(self) -> Optional[Path]:
        return self._get_path("", constants.THUMBNAIL_EXT_DEFAULT)
