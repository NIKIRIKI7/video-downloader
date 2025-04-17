import os

# --- Directory ---
VIDEO_DIR_DEFAULT = "video_output" # Default directory name

# --- External Tools (Optional: Set path directly if not in PATH) ---
# Example: FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"
FFMPEG_PATH: str | None = None
YTDLP_PATH: str | None = None

# --- yt-dlp Settings ---
# DEFAULTS - These will be configurable via GUI
SUB_LANG_DEFAULT = "en" # Default source language for subtitles
SUB_FORMAT_DEFAULT = "vtt"
YT_DLP_FORMAT_DEFAULT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" # Format for downloading video+audio
VIDEO_FORMAT_EXT_DEFAULT = "mp4" # Target container format

# --- Translation Settings ---
# DEFAULTS - These will be configurable via GUI
TARGET_LANG_DEFAULT = "ru"
SOURCE_LANG_DEFAULT = "en"

# --- File Naming ---
META_SUFFIX = "meta"
# TRANSLATED_SUFFIX will now depend on the target language setting
SUBTITLE_EXT_DEFAULT = "vtt" # Now default, actual ext might vary if format changes
META_EXT_DEFAULT = "txt"
AUDIO_MIX_SUFFIX = "mixed"
THUMBNAIL_EXT_DEFAULT = "jpg" # Добавлено: Расширение по умолчанию для превью (yt-dlp может выбрать другое)

# --- FFmpeg Settings ---
# DEFAULTS - These will be configurable via GUI
ORIGINAL_VOLUME_DEFAULT = "0.0" # Default original audio volume (0.0 = mute, 1.0 = normal)
ADDED_VOLUME_DEFAULT = "1.0"  # Default added (Yandex) audio volume
MERGED_AUDIO_CODEC_DEFAULT = "aac" # Output audio codec after merging

# --- GUI ---
QUEUE_POLL_INTERVAL_MS = 100 # Check ViewModel queue interval (milliseconds)

# --- Trimming ---
# Можно добавить константы по умолчанию для времени обрезки, если нужно
TRIM_START_TIME_DEFAULT = "00:00:00.000"
TRIM_END_TIME_DEFAULT = "00:00:10.000"