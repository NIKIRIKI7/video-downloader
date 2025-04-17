from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import get_tool_path
import subprocess
import os

class MergeAudio(ActionCommand):
    """Command to merge video audio with an external audio file using ffmpeg, based on context settings."""

    def execute(self, context: ProcessingContext) -> None:
        """Merges the video's audio with the Yandex audio file using context volume/codec settings."""
        if not context.video_path:
            # This might be acceptable if the user didn't request video download but wants to merge later.
            # However, the current flow likely depends on video_path being set.
            # Let's make it an error for now.
            self.log("[ERROR] Cannot merge audio: Video path not found in context (was 'Download Video' action run successfully?).")
            raise ValueError("Video path is missing in context for audio merge.")
        if not context.yandex_audio:
            # If 'da' action was selected, this should have been validated by GUI/Service,
            # but double-check here.
            self.log("[ERROR] Cannot merge audio: Yandex audio path not provided in context.")
            raise ValueError("Yandex audio path is missing in context for audio merge.")
        if not context.base:
            self.log("[ERROR] Cannot merge audio: Base filename not set in context.")
            raise ValueError("Base filename not set in context for audio merge.")

        video_path = context.video_path
        yandex_audio_path = context.yandex_audio

        # Read settings from context
        try:
            # Validate volume strings are valid floats before passing to ffmpeg
            original_volume_float = float(context.original_volume)
            added_volume_float = float(context.added_volume)
            original_volume = context.original_volume # Keep as string for command
            added_volume = context.added_volume     # Keep as string for command
        except ValueError:
            self.log(f"[ERROR] Invalid volume setting found: Original='{context.original_volume}', Added='{context.added_volume}'. Must be numbers.")
            raise ValueError("Invalid volume setting provided.")

        merged_audio_codec = context.merged_audio_codec
        if not merged_audio_codec:
            self.log("[ERROR] Merged audio codec is not specified in context.")
            raise ValueError("Merged audio codec is required.")

        # Get output path using context method
        output_path = context.get_merged_video_filepath()
        if not output_path:
            self.log("[ERROR] Cannot determine merged video output path.")
            raise ValueError("Could not determine merged video output path.")

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
             context.merged_video_path = output_path # Ensure context is aware
             return

        ffmpeg_path = get_tool_path('ffmpeg')

        self.log(f"[INFO] Merging audio tracks into: {output_path}")
        self.log(f"[DEBUG] Video Input: {video_path}")
        self.log(f"[DEBUG] Audio Input: {yandex_audio_path}")
        self.log(f"[DEBUG] Original Volume: {original_volume}") # Log volume setting (already represents factor)
        self.log(f"[DEBUG] Added Volume: {added_volume}")     # Log volume setting
        self.log(f"[DEBUG] Output Codec: {merged_audio_codec}")

        # ffmpeg command using filter_complex for mixing
        cmd = [
            ffmpeg_path,
            "-y",  # Overwrite output without asking
            "-i", video_path,             # Input 0: Original video
            "-i", yandex_audio_path,      # Input 1: Added audio
            "-filter_complex",
                # Use volume settings directly from context variables
                # These already represent the desired volume factor (e.g., 0.4 = 40%, 1.0 = 100%)
                f"[0:a]volume={original_volume}[a0];"
                f"[1:a]volume={added_volume}[a1];"
                f"[a0][a1]amix=inputs=2:duration=first[aout]", # Mix streams, duration based on first input (video)
            "-map", "0:v",          # Map video stream from input 0
            "-map", "[aout]",       # Map mixed audio stream from filter
            "-c:v", "copy",         # Copy video codec (fast, assumes compatible)
            "-c:a", merged_audio_codec, # Encode mixed audio using codec from context
            # "-b:a", "192k",       # Optional: Set audio bitrate if needed
            output_path             # Output file
        ]
        # Log the exact command being run for debugging
        self.log(f"[DEBUG] Executing FFmpeg command: {' '.join(cmd)}")

        try:
            # Use run, capture output, check for errors
            process = subprocess.run(cmd, check=True, capture_output=True, text=True, encoding='utf-8', errors='replace')
            # ffmpeg often logs to stderr even on success, check DEBUG log if needed
            # self.log(f"[DEBUG] ffmpeg output:\nSTDOUT:\n{process.stdout}\nSTDERR:\n{process.stderr}")

            if os.path.exists(output_path):
                context.merged_video_path = output_path
                self.log(f"[INFO] Audio merged successfully: {output_path}")
                # Add extra log emphasizing the output file
                self.log(f"[INFO] >>> Final video with mixed audio: {output_path} <<<")
            else:
                # This case indicates ffmpeg finished (exit code 0) but the file is missing
                self.log(f"[ERROR] Merged video file not found after successful ffmpeg command: {output_path}")
                self.log(f"[DEBUG] ffmpeg stdout:\n{process.stdout}")
                self.log(f"[DEBUG] ffmpeg stderr:\n{process.stderr}")
                raise FileNotFoundError(f"Merged video file not found despite ffmpeg success: {output_path}")

        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] ffmpeg failed during audio merge: {e}")
            self.log(f"[ERROR] Command: {' '.join(cmd)}") # Log command on error
            stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
            self.log(f"[ERROR] Stderr: {stderr_output}") # ffmpeg errors usually here
            raise
        except Exception as e:
            self.log(f"[ERROR] Unexpected error during audio merge: {type(e).__name__} - {e}")
            raise