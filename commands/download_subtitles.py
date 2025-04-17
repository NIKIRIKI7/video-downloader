from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
import os

class DownloadSubtitles(ActionCommand):
    """Command to download subtitles using yt-dlp, based on context settings."""

    def execute(self, context: ProcessingContext) -> None:
        """Downloads subtitles in the specified language and format from context."""
        if not context.base:
            self.log("[ERROR] Cannot download subtitles: 'base' filename not set.")
            raise ValueError("Base filename not set in context.")

        url = context.url
        output_dir = context.output_dir
        ensure_dir(output_dir)

        # Read settings from context
        lang = context.subtitle_lang
        sub_format = context.subtitle_format

        if not lang:
            self.log("[ERROR] Subtitle download language is not specified in context.")
            raise ValueError("Subtitle download language is required.")
        if not sub_format:
             self.log("[ERROR] Subtitle format is not specified in context.")
             raise ValueError("Subtitle format is required.")


        # Get expected path using context method (which uses subtitle_format)
        expected_sub_path = context.get_subtitle_filepath(lang)

        if not expected_sub_path:
             self.log("[ERROR] Cannot determine subtitle file path.")
             raise ValueError("Could not determine subtitle file path.")

        # Check if file already exists
        if os.path.exists(expected_sub_path):
            self.log(f"[WARN] Subtitle file already exists: {expected_sub_path}. Skipping download.")
            context.subtitle_path = expected_sub_path # Ensure context is aware
            return

        yt_dlp_path = get_tool_path('yt-dlp')
        # Output template for yt-dlp (name only, tool adds lang/ext)
        output_template = os.path.join(output_dir, f"{context.base}") # No extension here

        self.log(f"[INFO] Downloading subtitles ({lang}, {sub_format})...")
        cmd = [
            yt_dlp_path,
            "--encoding", "utf-8", # Explicitly request UTF-8
            "--no-playlist",
            "--skip-download", # Only subs
            "--write-sub",
            "--sub-lang", lang,
            "--convert-subs", sub_format, # Use format from context
            "-o", output_template, # Base path for output naming
            url
        ]

        try:
            # Use run with check=True for better error handling
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            # self.log(f"[DEBUG] yt-dlp output (subtitles):\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}") # Log if needed

            # Verify the expected file exists
            if os.path.exists(expected_sub_path):
                context.subtitle_path = expected_sub_path
                self.log(f"[INFO] Subtitles downloaded successfully: {expected_sub_path}")
            else:
                # Sometimes yt-dlp creates filename without lang code if only one lang downloaded
                # Check using the format specified in the context
                alt_sub_path = context._get_path("", sub_format) # e.g., base.vtt (or base.srt if format is srt)
                if alt_sub_path and os.path.exists(alt_sub_path):
                    self.log(f"[WARN] Subtitle found as {os.path.basename(alt_sub_path)}. Renaming to {os.path.basename(expected_sub_path)}.")
                    try:
                        os.rename(alt_sub_path, expected_sub_path)
                        context.subtitle_path = expected_sub_path
                        self.log(f"[INFO] Subtitles ready: {expected_sub_path}")
                    except OSError as rename_err:
                         self.log(f"[ERROR] Failed to rename subtitle file: {rename_err}")
                         # If rename fails, use the path as it was downloaded
                         context.subtitle_path = alt_sub_path
                else:
                    # Check stderr for common "no subtitles" message
                    stderr_lower = process.stderr.lower()
                    no_subs_found = False
                    if f"no subtitles found for languages: {lang}" in stderr_lower:
                        no_subs_found = True
                    elif f"unable to download video subtitles for languages: {lang}" in stderr_lower:
                         no_subs_found = True
                    # Add more patterns if needed based on yt-dlp output variations
                    elif "requested format is not available" in stderr_lower and "--write-sub" in " ".join(cmd):
                        # Might indicate general subtitle issue
                         no_subs_found = True


                    if no_subs_found:
                         self.log(f"[WARN] No subtitles available in '{lang}' for this video (or format '{sub_format}' not available).")
                         # Context.subtitle_path remains None. This is not a failure of the process.
                    else:
                         self.log(f"[ERROR] Expected subtitle file not found after download: {expected_sub_path}")
                         self.log(f"[DEBUG] yt-dlp stdout:\n{process.stdout}")
                         self.log(f"[DEBUG] yt-dlp stderr:\n{process.stderr}")
                         # Don't raise an error here, maybe the user only wanted video
                         # Logged as error, but processing continues.
                         # Consider if this should be a fatal error based on workflow needs.

        except subprocess.CalledProcessError as e:
            # Decode stderr for logging
            stderr_lower = e.stderr.decode('utf-8', errors='replace').lower() if isinstance(e.stderr, bytes) else e.stderr.lower()
            # Check stderr for "no subtitles" message even on error exit code
            no_subs_found_err = False
            if f"no subtitles found for languages: {lang}" in stderr_lower:
                no_subs_found_err = True
            elif f"unable to download video subtitles for languages: {lang}" in stderr_lower:
                no_subs_found_err = True
            elif "requested format is not available" in stderr_lower and "--write-sub" in " ".join(e.cmd):
                 no_subs_found_err = True

            if no_subs_found_err:
                 self.log(f"[WARN] No subtitles available in '{lang}' for this video (reported by yt-dlp error). Format: '{sub_format}'.")
                 # Not a critical error for the overall flow, context.subtitle_path remains None
            else:
                # Log the actual error
                self.log(f"[ERROR] yt-dlp failed while downloading subtitles: {e}")
                self.log(f"[ERROR] Command: {' '.join(e.cmd)}")
                # Ensure stderr is logged correctly as string
                stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
                self.log(f"[ERROR] Stderr: {stderr_output}")
                # Re-raise the exception as it's an unexpected error
                raise
        except Exception as e:
            self.log(f"[ERROR] Unexpected error downloading subtitles: {type(e).__name__} - {e}")
            raise