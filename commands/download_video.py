from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
import os

class DownloadVideo(ActionCommand):
    """Command to download the video itself using yt-dlp, based on context settings."""

    def execute(self, context: ProcessingContext) -> None:
        """Downloads the video file according to context format settings."""
        if not context.base:
            self.log("[ERROR] Cannot download video: 'base' filename not set in context.")
            raise ValueError("Base filename not set in context before downloading video.")

        url = context.url
        output_dir = context.output_dir
        ensure_dir(output_dir)

        # Read settings from context
        yt_dlp_format = context.yt_dlp_format
        video_format_ext = context.video_format_ext

        if not yt_dlp_format:
            self.log("[ERROR] yt-dlp download format is not specified in context.")
            raise ValueError("yt-dlp download format is required.")
        if not video_format_ext:
             self.log("[ERROR] Video output format extension is not specified in context.")
             raise ValueError("Video output format extension is required.")

        # Get expected path using context method (which uses video_format_ext)
        expected_video_path = context.get_video_filepath()
        if not expected_video_path:
            self.log("[ERROR] Cannot determine video file path.")
            raise ValueError("Could not determine video file path.")

        # Check if target file already exists
        if os.path.exists(expected_video_path):
             self.log(f"[WARN] Video file already exists: {expected_video_path}. Skipping download.")
             context.video_path = expected_video_path # Ensure context path is set
             return

        yt_dlp_path = get_tool_path('yt-dlp')
        # Output template uses base name, yt-dlp adds extension based on download/merge
        output_template = os.path.join(output_dir, f"{context.base}.%(ext)s")

        self.log(f"[INFO] Downloading video (format: '{yt_dlp_format}', container: '{video_format_ext}') to {output_dir}...")
        cmd = [
            yt_dlp_path,
            "--encoding", "utf-8",
            "--no-playlist",
            "--format", yt_dlp_format, # Use format from context
            # Ensure the final merged file has the desired extension
            "--merge-output-format", video_format_ext, # Use extension from context
            # Remove other writes handled by separate commands
            # "--write-description", # Handled by DownloadMetadata
            # "--write-sub", # Handled by DownloadSubtitles
            "-o", output_template,
            url
        ]
        # Log the command
        self.log(f"[DEBUG] Executing yt-dlp command: {' '.join(cmd)}")

        try:
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            # Log sparingly unless debug is needed
            # self.log(f"[DEBUG] yt-dlp output (video):\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}")

            # Verify expected file was created
            if os.path.exists(expected_video_path):
                context.video_path = expected_video_path
                self.log(f"[INFO] Video downloaded successfully: {expected_video_path}")
            else:
                # Search for the file with the correct base but potentially different extension
                # This might happen if merging failed or wasn't needed, and the originally
                # downloaded file (e.g., .webm) remained.
                found_path = None
                self.log(f"[DEBUG] Expected video path '{expected_video_path}' not found. Searching directory '{output_dir}' for '{context.base}.*'")
                for fname in os.listdir(output_dir):
                    f_base, f_ext = os.path.splitext(fname)
                    # Check if base name matches and it's not a temporary/part file
                    if f_base == context.base and f_ext and f_ext.lower() not in [".part", ".ytdl"]:
                        actual_path = os.path.join(output_dir, fname)
                        if os.path.isfile(actual_path): # Check if it's a file
                             self.log(f"[DEBUG] Found potential match: {actual_path}")
                             found_path = actual_path
                             break # Take the first match

                if found_path:
                     # If found path is not the expected one, log a warning.
                     if found_path != expected_video_path:
                        self.log(f"[WARN] Video downloaded as {os.path.basename(found_path)}, expected {os.path.basename(expected_video_path)}. Using actual file.")
                     else:
                         # This case should technically be caught by the 'if exists' above, but safe check.
                         self.log(f"[INFO] Video downloaded successfully: {found_path}")
                     context.video_path = found_path # Use the actual path found
                else:
                     # If still not found, it's an error.
                     self.log(f"[ERROR] Expected video file not found after download: {expected_video_path} (and no alternatives like '{context.base}.*' found).")
                     # Log yt-dlp output for debugging
                     self.log(f"[DEBUG] yt-dlp stdout:\n{process.stdout}")
                     self.log(f"[DEBUG] yt-dlp stderr:\n{process.stderr}")
                     raise FileNotFoundError(f"Expected video file '{expected_video_path}' or alternative not found after download.")

        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] yt-dlp failed while downloading video: {e}")
            self.log(f"[ERROR] Command: {' '.join(e.cmd)}")
            stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
            self.log(f"[ERROR] Stderr: {stderr_output}")
            raise
        except Exception as e:
            self.log(f"[ERROR] Unexpected error downloading video: {type(e).__name__} - {e}")
            raise