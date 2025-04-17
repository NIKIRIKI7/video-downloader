from commands.base_command import ActionCommand, LoggerCallable
from commands.download_video import DownloadVideo
from commands.download_subtitles import DownloadSubtitles
from commands.translate_subtitles import TranslateSubtitles
from commands.download_metadata import DownloadMetadata
from commands.translate_metadata import TranslateMetadata # Keep available if needed
from commands.merge_audio import MergeAudio
from model.processing_context import ProcessingContext # Use the context object
from utils.utils import find_executable
import constants
from typing import List, Dict, Any, Optional, Type

class VideoService:
    """
    Service orchestrating video processing operations using commands.
    """
    COMMAND_MAPPING: Dict[str, Type[ActionCommand]] = {
        'md': DownloadMetadata,
        'dv': DownloadVideo,
        'ds': DownloadSubtitles,
        'dt': TranslateSubtitles,
        'da': MergeAudio,
        # 'tm': TranslateMetadata, # Action key for translating metadata (if checkbox added)
    }

    # Define dependencies: commands requiring 'md' (DownloadMetadata)
    METADATA_DEPENDENCIES = {'dv', 'ds', 'dt', 'da', 'tm'}

    # Define tool dependencies for actions
    TOOL_DEPENDENCIES: Dict[str, List[str]] = {
        'md': ['yt-dlp'],
        'dv': ['yt-dlp'], # ffmpeg might be needed by yt-dlp for merging
        'ds': ['yt-dlp'],
        'dt': [], # Requires deep_translator, pysubs2 (Python libs)
        'da': ['ffmpeg'],
        'tm': [], # Requires deep_translator (Python lib)
    }

    def __init__(self, logger: LoggerCallable):
        """
        Initializes the service.

        Args:
            logger: Function for logging messages.
        """
        self.logger: LoggerCallable = logger

    def _check_tool_availability(self, actions: List[str]) -> bool:
        """Checks if required external tools for selected actions are available."""
        required_tools = set()
        for action in actions:
            required_tools.update(self.TOOL_DEPENDENCIES.get(action, []))

        all_tools_found = True
        for tool in required_tools:
             path_const = getattr(constants, f"{tool.upper()}_PATH", None)
             if not find_executable(tool, path_const):
                 self.logger(f"[ERROR] Required tool '{tool}' not found. Please install it or check PATH/constants.py.")
                 all_tools_found = False
        return all_tools_found


    def perform_actions(self, url: str, yandex_audio: Optional[str], actions: List[str], output_dir: str) -> bool:
        """
        Executes the requested actions in a defined order.

        Args:
            url: Video URL.
            yandex_audio: Path to Yandex audio file (optional).
            actions: List of action keys (e.g., ['md', 'dv', 'da']).
            output_dir: Directory to save output files.

        Returns:
            True if all requested actions succeeded, False otherwise.
        """
        self.logger(f"[INFO] Starting video processing for URL: {url}")
        self.logger(f"[INFO] Output directory: {output_dir}")
        self.logger(f"[INFO] Requested actions: {actions}")

        # 1. Check tool availability early
        if not self._check_tool_availability(actions):
             self.logger("[ERROR] Aborting due to missing required tools.")
             return False

        # 2. Prepare context
        context = ProcessingContext(url=url, yandex_audio=yandex_audio, output_dir=output_dir)

        # 3. Determine execution order (ensure 'md' runs first if needed)
        ordered_actions = actions[:]
        needs_metadata = any(action in self.METADATA_DEPENDENCIES for action in ordered_actions)

        if needs_metadata and 'md' not in ordered_actions:
            ordered_actions.insert(0, 'md')
            self.logger("[INFO] Added 'Download Metadata' action as it's required by other selected actions.")
        elif 'md' in ordered_actions and ordered_actions.index('md') != 0:
            ordered_actions.remove('md')
            ordered_actions.insert(0, 'md')
            self.logger("[INFO] Ensuring 'Download Metadata' runs first.")

        self.logger(f"[INFO] Execution order: {ordered_actions}")

        # 4. Execute commands
        success = True
        for action_key in ordered_actions:
            command_class = self.COMMAND_MAPPING.get(action_key)
            if not command_class:
                self.logger(f"[WARN] Unknown action key '{action_key}', skipping.")
                continue

            command_instance = command_class(self.logger)
            action_name = command_instance.__class__.__name__
            self.logger(f"▶ Executing: {action_name}...")

            try:
                # Pre-condition check (redundant if ordering is correct, but safe)
                if action_key in self.METADATA_DEPENDENCIES and context.base is None:
                    self.logger(f"[ERROR] Cannot execute '{action_name}': Metadata ('base' name) is missing. Was 'md' skipped or failed?")
                    success = False
                    break # Stop processing chain

                # Execute the command
                command_instance.execute(context)
                self.logger(f"✔ Finished: {action_name}.")

            except FileNotFoundError as e:
                # Specific handling for missing tools/files if not caught earlier
                self.logger(f"✖ File/Tool Error during {action_name}: {e}")
                success = False
                break
            except subprocess.CalledProcessError as e:
                # Error from external tool execution
                self.logger(f"✖ External Tool Error during {action_name}: {e}")
                # Command should have logged details (stderr)
                success = False
                break
            except Exception as e:
                # Catch-all for other unexpected errors in the command
                self.logger(f"✖ Unexpected Error during {action_name}: {type(e).__name__} - {e}")
                import traceback
                self.logger(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
                success = False
                break

        # 5. Final status
        if success:
            self.logger("🎉 All selected actions completed successfully.")
            # Log final paths from context
            self.logger("[INFO] --- Generated Files ---")
            if context.metadata_path and os.path.exists(context.metadata_path): self.logger(f"[INFO] Metadata: {context.metadata_path}")
            if context.translated_metadata_path and os.path.exists(context.translated_metadata_path): self.logger(f"[INFO] Translated Metadata: {context.translated_metadata_path}")
            if context.video_path and os.path.exists(context.video_path): self.logger(f"[INFO] Video: {context.video_path}")
            if context.subtitle_path and os.path.exists(context.subtitle_path): self.logger(f"[INFO] Subtitles ({constants.SUB_LANG}): {context.subtitle_path}")
            if context.translated_subtitle_path and os.path.exists(context.translated_subtitle_path): self.logger(f"[INFO] Translated Subtitles ({constants.TARGET_LANG}): {context.translated_subtitle_path}")
            if context.merged_video_path and os.path.exists(context.merged_video_path): self.logger(f"[INFO] Merged Audio Video: {context.merged_video_path}")
            self.logger("[INFO] ---------------------")
        else:
            self.logger("❌ Processing stopped due to an error.")

        return success