from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import ensure_dir, get_tool_path
import subprocess
import json
import os
import re # For cleaning filenames

class DownloadMetadata(ActionCommand):
    """Command to download video metadata using yt-dlp."""

    def execute(self, context: ProcessingContext) -> None:
        """
        Downloads metadata, saves it, and populates context.base, title, etc.
        """
        url = context.url
        output_dir = context.output_dir
        ensure_dir(output_dir)

        self.log("[INFO] Requesting metadata...")
        yt_dlp_path = get_tool_path('yt-dlp') # Raises FileNotFoundError if not found

        try:
            cmd = [yt_dlp_path, "--no-playlist", "--dump-single-json", "--skip-download", url]
            # Set encoding explicitly for check_output
            result = subprocess.check_output(cmd, text=True, encoding='utf-8', stderr=subprocess.PIPE)
            data = json.loads(result)

            video_id = data.get('id', '')
            title = data.get('title', 'untitled')
            description = data.get('description', '')
            tags = data.get('tags', [])

            # --- Determine base filename (prioritize ID) ---
            raw_base = video_id if video_id else title
            # Clean the base name: remove invalid chars, replace spaces, limit length
            safe_base = re.sub(r'[<>:"/\\|?*]', '_', raw_base) # Remove forbidden chars
            safe_base = re.sub(r'\s+', '_', safe_base) # Replace whitespace with underscore
            safe_base = safe_base[:100] # Limit length to avoid issues
            if not safe_base: # Handle edge case of empty name
                safe_base = "video"
            context.base = safe_base
            # ---

            context.title = title
            context.description = description
            context.tags = tags

            # Save metadata to file - uses context method which now uses defaults/settings
            # Pass None for lang to get original metadata path
            meta_path = context.get_metadata_filepath(lang=None)
            if not meta_path:
                 self.log("[ERROR] Cannot determine metadata file path (base name missing?).")
                 # Raise error as this path is critical
                 raise ValueError("Metadata file path could not be determined (base name missing).")

            context.metadata_path = meta_path # Store path in context
            self.log(f"[INFO] Saving metadata to: {meta_path}")
            try:
                with open(meta_path, 'w', encoding='utf-8') as f:
                    f.write(f"ID: {video_id}\n")
                    f.write(f"Title: {title}\n\n")
                    f.write(f"Description:\n{description}\n\n")
                    f.write(f"Tags: {', '.join(tags)}")
                self.log("[INFO] Metadata saved successfully.")
            except IOError as e:
                self.log(f"[ERROR] Failed to write metadata file {meta_path}: {e}")
                # Propagate the error
                raise

        except subprocess.CalledProcessError as e:
            self.log(f"[ERROR] yt-dlp failed while fetching metadata: {e}")
            self.log(f"[ERROR] Command: {' '.join(e.cmd)}")
            # Decode stderr for logging if captured as bytes
            stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
            self.log(f"[ERROR] Stderr: {stderr_output}")
            raise
        except json.JSONDecodeError as e:
            self.log(f"[ERROR] Failed to decode JSON from yt-dlp: {e}")
            # Ensure 'result' is defined before logging
            log_data = result[:500] if 'result' in locals() else "N/A"
            self.log(f"[DEBUG] Received data (partial): {log_data}...")
            raise
        except Exception as e:
            self.log(f"[ERROR] Unexpected error downloading metadata: {type(e).__name__} - {e}")
            raise