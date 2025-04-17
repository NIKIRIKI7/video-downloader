from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import constants
import subprocess
import os

class DownloadVideo(ActionCommand):
    """Command to download the video itself using yt-dlp."""

    def execute(self, context: ProcessingContext) -> None:
        """Downloads the video file."""
        if not context.base:
            self.log("[ERROR] Cannot download video: 'base' filename not set in context.")
            raise ValueError("Base filename not set in context before downloading video.")

        url = context.url
        output_dir = context.output_dir
        ensure_dir(output_dir)

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
        output_template = os.path.join(output_dir, f"{context.base}.%(ext)s")

        self.log(f"[INFO] Downloading video ({constants.YT_DLP_FORMAT}) to {output_dir}...")
        cmd = [
            yt_dlp_path,
            "--no-playlist",
            "--format", constants.YT_DLP_FORMAT,
            "--merge-output-format", constants.VIDEO_FORMAT_EXT,
            # Remove other writes if handled by separate commands
            # "--write-description",
            # "--write-sub", "--sub-lang", constants.SUB_LANG, "--convert-subs", constants.SUB_FORMAT,
            "-o", output_template,
            url
        ]

        try:
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            # Log sparingly unless debug is needed
            # self.log(f"[DEBUG] yt-dlp output (video):\n{process.stdout}\n{process.stderr}")

            # Verify expected file was created
            if os.path.exists(expected_video_path):
                context.video_path = expected_video_path
                self.log(f"[INFO] Video downloaded successfully: {expected_video_path}")
            else:
                # Search for the file with the correct base but potentially different extension
                found_path = None
                for fname in os.listdir(output_dir):
                    f_base, f_ext = os.path.splitext(fname)
                    if f_base == context.base and f_ext and f_ext != ".part": # Ignore partial downloads
                        actual_path = os.path.join(output_dir, fname)
                        if os.path.exists(actual_path):
                             found_path = actual_path
                             break
                if found_path:
                     self.log(f"[WARN] Video downloaded as {os.path.basename(found_path)}, expected {os.path.basename(expected_video_path)}. Using actual file.")
                     context.video_path = found_path # Use the actual path
                else:
                     self.log(f"[ERROR] Expected video file not found after download: {expected_video_path}")
                     # Log yt-dlp output for debugging
                     self.log(f"[DEBUG] yt-dlp stdout:\n{process.stdout}")
                     self.log(f"[DEBUG] yt-dlp stderr:\n{process.stderr}")
                     raise FileNotFoundError(f"Expected video file not found: {expected_video_path}")

        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] yt-dlp failed while downloading video: {e}")
            self.log(f"[ERROR] Command: {' '.join(e.cmd)}")
            self.log(f"[ERROR] Stderr: {e.stderr}")
            raise
        except Exception as e:
            self.log(f"[ERROR] Unexpected error downloading video: {type(e).__name__} - {e}")
            raise