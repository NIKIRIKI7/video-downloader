from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import get_tool_path
import constants
import subprocess
import os

class MergeAudio(ActionCommand):
    """Command to merge video audio with an external audio file using ffmpeg."""

    def execute(self, context: ProcessingContext) -> None:
        """Merges the video's audio with the Yandex audio file."""
        if not context.video_path:
            self.log("[WARN] Skipping audio merge: Video path not found in context.")
            return
        if not context.yandex_audio:
            self.log("[WARN] Skipping audio merge: Yandex audio path not provided.")
            return
        if not context.base:
            self.log("[WARN] Skipping audio merge: Base filename not set.")
            return

        video_path = context.video_path
        yandex_audio_path = context.yandex_audio
        output_path = context.get_merged_video_filepath()

        if not output_path:
            self.log("[ERROR] Cannot determine merged video output path.")
            return

        # Input file checks
        if not os.path.exists(video_path):
            self.log(f"[ERROR] Audio merge failed: Input video file not found: {video_path}")
            raise FileNotFoundError(f"Input video file not found: {video_path}")
        if not os.path.exists(yandex_audio_path):
            self.log(f"[ERROR] Audio merge failed: Yandex audio file not found: {yandex_audio_path}")
            raise FileNotFoundError(f"Yandex audio file not found: {yandex_audio_path}")

        # Check if output exists
        if os.path.exists(output_path):
             self.log(f"[WARN] Merged video file already exists: {output_path}. Skipping merge.")
             context.merged_video_path = output_path
             return

        ffmpeg_path = get_tool_path('ffmpeg')

        self.log(f"[INFO] Merging audio tracks into: {output_path}")
        self.log(f"[DEBUG] Video Input: {video_path}")
        self.log(f"[DEBUG] Audio Input: {yandex_audio_path}")

        # ffmpeg command using filter_complex for mixing
        cmd = [
            ffmpeg_path,
            "-y",  # Overwrite output without asking
            "-i", video_path,             # Input 0: Original video
            "-i", yandex_audio_path,      # Input 1: Yandex audio
            "-filter_complex",
                f"[0:a]volume={constants.ORIGINAL_VOLUME}[a0];" # Original audio stream + volume
                f"[1:a]volume={constants.ADDED_VOLUME}[a1];"   # Yandex audio stream + volume
                f"[a0][a1]amix=inputs=2:duration=first[aout]", # Mix streams, duration based on video
            "-map", "0:v",          # Map video stream from input 0
            "-map", "[aout]",       # Map mixed audio stream
            "-c:v", "copy",         # Copy video codec (fast)
            "-c:a", constants.MERGED_AUDIO_CODEC, # Encode mixed audio
            # "-b:a", "192k",       # Optional: Set audio bitrate
            output_path             # Output file
        ]

        try:
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8')
            # ffmpeg often logs to stderr even on success
            # self.log(f"[DEBUG] ffmpeg output:\n{process.stdout}\n{process.stderr}")

            if os.path.exists(output_path):
                context.merged_video_path = output_path
                self.log(f"[INFO] Audio merged successfully: {output_path}")
            else:
                self.log(f"[ERROR] Merged video file not found after ffmpeg command: {output_path}")
                self.log(f"[DEBUG] ffmpeg stdout:\n{process.stdout}")
                self.log(f"[DEBUG] ffmpeg stderr:\n{process.stderr}")
                raise FileNotFoundError(f"Merged video file not found: {output_path}")

        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] ffmpeg failed during audio merge: {e}")
            self.log(f"[ERROR] Command: {' '.join(e.cmd)}")
            self.log(f"[ERROR] Stderr: {e.stderr}") # ffmpeg errors usually here
            raise
        except Exception as e:
            self.log(f"[ERROR] Unexpected error during audio merge: {type(e).__name__} - {e}")
            raise