from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import constants
import subprocess
import os

class DownloadSubtitles(ActionCommand):
    """Command to download subtitles using yt-dlp."""

    def execute(self, context: ProcessingContext) -> None:
        """Downloads subtitles in the specified language and format."""
        if not context.base:
            self.log("[ERROR] Cannot download subtitles: 'base' filename not set.")
            raise ValueError("Base filename not set in context.")

        url = context.url
        output_dir = context.output_dir
        ensure_dir(output_dir)

        lang = constants.SUB_LANG
        sub_format = constants.SUB_FORMAT
        expected_sub_path = context.get_subtitle_filepath(lang)

        if not expected_sub_path:
             self.log("[ERROR] Cannot determine subtitle file path.")
             raise ValueError("Could not determine subtitle file path.")

        # Check if file already exists
        if os.path.exists(expected_sub_path):
            self.log(f"[WARN] Subtitle file already exists: {expected_sub_path}. Skipping download.")
            context.subtitle_path = expected_sub_path
            return

        yt_dlp_path = get_tool_path('yt-dlp')
        # Output template for yt-dlp (name only, extension/lang added by tool)
        output_template = os.path.join(output_dir, f"{context.base}") # No extension here

        self.log(f"[INFO] Downloading subtitles ({lang}, {sub_format})...")
        cmd = [
            yt_dlp_path,
            "--no-playlist",
            "--skip-download", # Only subs
            "--write-sub",
            "--sub-lang", lang,
            "--convert-subs", sub_format,
            "-o", output_template, # Base path for output naming
            url
        ]

        try:
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            # self.log(f"[DEBUG] yt-dlp output (subtitles):\n{process.stdout}\n{process.stderr}") # Log if needed

            # Verify the expected file exists
            if os.path.exists(expected_sub_path):
                context.subtitle_path = expected_sub_path
                self.log(f"[INFO] Subtitles downloaded successfully: {expected_sub_path}")
            else:
                # Sometimes yt-dlp creates filename without lang code if only one lang downloaded
                alt_sub_path = context._get_path("", sub_format) # e.g., base.vtt
                if alt_sub_path and os.path.exists(alt_sub_path):
                    self.log(f"[WARN] Subtitle found as {os.path.basename(alt_sub_path)}. Renaming to {os.path.basename(expected_sub_path)}.")
                    try:
                        os.rename(alt_sub_path, expected_sub_path)
                        context.subtitle_path = expected_sub_path
                        self.log(f"[INFO] Subtitles ready: {expected_sub_path}")
                    except OSError as rename_err:
                         self.log(f"[ERROR] Failed to rename subtitle file: {rename_err}")
                         context.subtitle_path = alt_sub_path # Use the alternative path if rename fails
                else:
                    # Check stderr for common "no subtitles" message
                    stderr_lower = process.stderr.lower()
                    if f"no subtitles found for languages: {lang}" in stderr_lower or \
                       f"unable to download video subtitles" in stderr_lower:
                         self.log(f"[WARN] No subtitles available in '{lang}' for this video.")
                         # Not an error, just no subs. Context.subtitle_path remains None.
                    else:
                         self.log(f"[ERROR] Expected subtitle file not found after download: {expected_sub_path}")
                         self.log(f"[DEBUG] yt-dlp stdout:\n{process.stdout}")
                         self.log(f"[DEBUG] yt-dlp stderr:\n{process.stderr}")
                         # Don't raise, allow process to continue, but log error
                         # raise FileNotFoundError(f"Expected subtitle file not found: {expected_sub_path}")

        except subprocess.CalledProcessError as e:
             # Check stderr for "no subtitles" message even if it's an error exit code
            stderr_lower = e.stderr.lower()
            if f"no subtitles found for languages: {lang}" in stderr_lower or \
               f"unable to download video subtitles" in stderr_lower:
                 self.log(f"[WARN] No subtitles available in '{lang}' for this video (reported by yt-dlp error).")
                 # Not a critical error for the flow
            else:
                self.log(f"[ERROR] yt-dlp failed while downloading subtitles: {e}")
                self.log(f"[ERROR] Command: {' '.join(e.cmd)}")
                self.log(f"[ERROR] Stderr: {e.stderr}")
                raise # Re-raise other errors
        except Exception as e:
            self.log(f"[ERROR] Unexpected error downloading subtitles: {type(e).__name__} - {e}")
            raise