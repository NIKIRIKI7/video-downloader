import os

# --- Directory ---
VIDEO_DIR_DEFAULT = "video_output" # Default directory name

# --- External Tools (Optional: Set path directly if not in PATH) ---
# Example: FFMPEG_PATH = "C:/ffmpeg/bin/ffmpeg.exe"
FFMPEG_PATH: str | None = None
YTDLP_PATH: str | None = None

# --- yt-dlp Settings ---
SUB_LANG = "en"
SUB_FORMAT = "vtt"
YT_DLP_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best" # Format for downloading video+audio
VIDEO_FORMAT_EXT = "mp4" # Target container format

# --- Translation Settings ---
TARGET_LANG = "ru"
SOURCE_LANG = "en"

# --- File Naming ---
META_SUFFIX = "meta"
TRANSLATED_SUFFIX = TARGET_LANG # e.g., ".ru"
SUBTITLE_EXT = "vtt"
META_EXT = "txt"
AUDIO_MIX_SUFFIX = "mixed"

# --- FFmpeg Settings ---
ORIGINAL_VOLUME = "0.7"
ADDED_VOLUME = "1.0"
MERGED_AUDIO_CODEC = "aac" # Output audio codec after merging

# --- GUI ---
QUEUE_POLL_INTERVAL_MS = 100 # Check ViewModel queue interval