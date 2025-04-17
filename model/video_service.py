from commands.base_command import ActionCommand, LoggerCallable
from commands.download_video import DownloadVideo
from commands.download_subtitles import DownloadSubtitles
from commands.translate_subtitles import TranslateSubtitles
from commands.download_metadata import DownloadMetadata
from commands.translate_metadata import TranslateMetadata
from commands.merge_audio import MergeAudio
from model.processing_context import ProcessingContext
from utils.utils import find_executable, get_tool_path # Added get_tool_path here if needed, usually used in commands
# Import constants only for defaults and mappings
import constants
import os
import subprocess # For specific exception handling
from typing import List, Dict, Any, Optional, Type

class VideoService:
    """
    Service orchestrating video processing operations using commands and context.
    """
    COMMAND_MAPPING: Dict[str, Type[ActionCommand]] = {
        'md': DownloadMetadata,
        'dv': DownloadVideo,
        'ds': DownloadSubtitles,
        'dt': TranslateSubtitles,
        'da': MergeAudio,
        'tm': TranslateMetadata, # Action key for translating metadata
    }

    # Define dependencies: commands requiring 'md' (DownloadMetadata) to have run first
    # to establish the 'base' filename in the context.
    METADATA_DEPENDENCIES = {'dv', 'ds', 'dt', 'da', 'tm'}

    # Define tool dependencies for actions
    TOOL_DEPENDENCIES: Dict[str, List[str]] = {
        'md': ['yt-dlp'],
        'dv': ['yt-dlp', 'ffmpeg'], # ffmpeg often needed by yt-dlp for merging formats
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
            # Get the list of tools for the action, default to empty list if action unknown
            required_tools.update(self.TOOL_DEPENDENCIES.get(action, []))

        if not required_tools:
             self.logger("[DEBUG] No external tools required for selected actions.")
             return True # No external tools needed

        self.logger(f"[DEBUG] Checking availability for tools: {required_tools}")
        all_tools_found = True
        for tool in required_tools:
             # Get configured path from constants (e.g., constants.FFMPEG_PATH)
             path_const_name = f"{tool.upper()}_PATH"
             configured_path = getattr(constants, path_const_name, None)

             # find_executable checks configured path first, then system PATH
             if not find_executable(tool, configured_path):
                 self.logger(f"[ERROR] Required tool '{tool}' not found.")
                 self.logger(f"[ERROR] Please install '{tool}' and ensure it's in your system PATH,")
                 self.logger(f"[ERROR] or set the full path in constants.py (variable: {path_const_name}).")
                 all_tools_found = False
             else:
                  # Optionally log where the tool was found
                  # tool_location = find_executable(tool, configured_path)
                  # self.logger(f"[DEBUG] Found required tool '{tool}' at: {tool_location}")
                  pass

        return all_tools_found


    def perform_actions(self, url: str, yandex_audio: Optional[str], actions: List[str], output_dir: str, settings: Dict[str, Any]) -> bool:
        """
        Executes the requested actions using provided settings, populating a ProcessingContext.

        Args:
            url: Video URL.
            yandex_audio: Path to external audio file (optional, used if 'da' in actions).
            actions: List of action keys (e.g., ['md', 'dv', 'da']).
            output_dir: Directory to save output files.
            settings: Dictionary containing configuration from the GUI/caller
                      (e.g., {'source_lang': 'en', 'target_lang': 'ru', 'original_volume': '0.0', ...})

        Returns:
            True if all requested actions succeeded without critical errors, False otherwise.
        """
        self.logger(f"[INFO] === Starting Video Processing ===")
        self.logger(f"[INFO] URL: {url}")
        self.logger(f"[INFO] Output Directory: {output_dir}")
        self.logger(f"[INFO] Requested Actions: {actions}")
        # Log settings carefully, could be large. Maybe log keys or specific important ones.
        # self.logger(f"[DEBUG] Using Settings: {settings}")
        self.logger(f"[INFO] Settings: Langs({settings.get('source_lang')}>{settings.get('target_lang')}), Subs({settings.get('subtitle_lang')}/{settings.get('subtitle_format')}), Video({settings.get('video_format_ext')}), Volume({settings.get('original_volume')}/{settings.get('added_volume')})")


        # 1. Check tool availability early
        if not self._check_tool_availability(actions):
             self.logger("[ERROR] Aborting processing due to missing required external tools.")
             return False

        # 2. Prepare ProcessingContext, passing all settings from the dictionary
        #    The context dataclass handles defaults if a key is missing from the settings dict.
        try:
            context = ProcessingContext(
                url=url,
                yandex_audio=yandex_audio,
                output_dir=output_dir,
                **settings # Unpack the settings dictionary directly into the context fields
            )
            self.logger(f"[DEBUG] Initialized ProcessingContext: {context}")
        except TypeError as e:
             # This might happen if settings dict contains unexpected keys
             self.logger(f"[ERROR] Failed to initialize ProcessingContext with provided settings: {e}")
             self.logger(f"[DEBUG] Provided settings: {settings}")
             return False


        # 3. Determine execution order: Ensure 'md' (DownloadMetadata) runs first if needed
        #    because it establishes the 'base' filename required by many other commands.
        ordered_actions = actions[:] # Create a copy to modify
        needs_metadata = any(action in self.METADATA_DEPENDENCIES for action in ordered_actions)

        if needs_metadata:
            if 'md' not in ordered_actions:
                # If 'md' is needed but not requested, add it to the beginning
                ordered_actions.insert(0, 'md')
                self.logger("[INFO] Action 'md' (Download Metadata) added as it's required by other selected actions.")
            elif ordered_actions.index('md') != 0:
                # If 'md' is requested but not first, move it to the beginning
                ordered_actions.remove('md')
                ordered_actions.insert(0, 'md')
                self.logger("[INFO] Action 'md' (Download Metadata) moved to the beginning as it's a prerequisite.")
        else:
            # If 'md' is not needed by any other action, its position doesn't matter relative to them.
            # If it was requested, leave it where it is. If not, it's not added.
             pass

        self.logger(f"[INFO] Final execution order: {ordered_actions}")


        # 4. Execute commands sequentially using the prepared context
        success = True
        for action_key in ordered_actions:
            command_class = self.COMMAND_MAPPING.get(action_key)
            if not command_class:
                self.logger(f"[WARN] Unknown action key '{action_key}', skipping.")
                continue

            command_instance = command_class(self.logger)
            action_name = command_instance.__class__.__name__
            self.logger(f"--- ▶ Executing: {action_name} ---")

            try:
                # Explicit pre-condition check: Does this action depend on metadata?
                if action_key in self.METADATA_DEPENDENCIES:
                    # If it depends on metadata, the context MUST have a 'base' name.
                    if context.base is None:
                        # This indicates 'md' was required but either skipped, failed,
                        # or didn't correctly set the base name. This is a fatal error for dependent steps.
                        self.logger(f"[ERROR] Cannot execute '{action_name}': Required 'base' filename is missing in context.")
                        self.logger("[ERROR] Ensure 'md' (Download Metadata) action runs successfully first.")
                        success = False
                        break # Stop processing chain

                # Execute the command's action. The command will use the context.
                command_instance.execute(context)
                self.logger(f"--- ✔ Finished: {action_name} ---")

            # Handle specific, expected exceptions from commands or tools
            except FileNotFoundError as e:
                # Likely a required file (input) or external tool was not found by the command.
                self.logger(f"✖ FILE/TOOL NOT FOUND during {action_name}: {e}")
                success = False
                break # Stop processing
            except subprocess.CalledProcessError as e:
                # An external tool (ffmpeg, yt-dlp) returned a non-zero exit code.
                # The command should have logged details (stderr).
                self.logger(f"✖ EXTERNAL TOOL FAILED during {action_name} (Exit Code: {e.returncode}). Check logs above for details.")
                # Stderr might be already logged by the command, but log again if needed:
                # stderr_output = e.stderr.decode('utf-8', errors='replace') if isinstance(e.stderr, bytes) else e.stderr
                # self.logger(f"[DEBUG] Failing command stderr: {stderr_output}")
                success = False
                break # Stop processing
            except ValueError as e:
                # Catch configuration errors or invalid data issues raised by commands.
                self.logger(f"✖ CONFIGURATION/VALUE ERROR during {action_name}: {e}")
                success = False
                break # Stop processing
            except IOError as e:
                 # Catch errors related to file reading/writing within commands.
                 self.logger(f"✖ FILE I/O ERROR during {action_name}: {e}")
                 success = False
                 break # Stop processing
            except Exception as e:
                # Catch any other unexpected errors within the command's execute method.
                self.logger(f"✖ UNEXPECTED ERROR during {action_name}: {type(e).__name__} - {e}")
                import traceback
                self.logger(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
                success = False
                break # Stop processing

        # 5. Final status reporting
        self.logger(f"[INFO] === Processing {'Completed' if success else 'Stopped'} ===")
        if success:
            self.logger("🎉 All selected actions completed successfully.")
            # Log final paths of potentially generated files using context methods
            # These methods use the settings stored within the context instance.
            self.logger("[INFO] --- Generated Files (Check existence) ---")
            if context.base: # Only log file paths if base name was determined
                meta_orig = context.get_metadata_filepath(lang=None)
                meta_trans = context.get_metadata_filepath(lang=context.target_lang)
                video_file = context.get_video_filepath()
                sub_orig = context.get_subtitle_filepath(lang=context.subtitle_lang)
                sub_trans = context.get_subtitle_filepath(lang=context.target_lang)
                merged_video = context.get_merged_video_filepath()

                if meta_orig and os.path.exists(meta_orig): self.logger(f"[INFO] Metadata (Original): {meta_orig}")
                if meta_trans and os.path.exists(meta_trans): self.logger(f"[INFO] Metadata ({context.target_lang}): {meta_trans}")
                if video_file and os.path.exists(video_file): self.logger(f"[INFO] Video ({context.video_format_ext}): {video_file}")
                if sub_orig and os.path.exists(sub_orig): self.logger(f"[INFO] Subtitles ({context.subtitle_lang}, {context.subtitle_format}): {sub_orig}")
                if sub_trans and os.path.exists(sub_trans): self.logger(f"[INFO] Subtitles ({context.target_lang}, {context.subtitle_format}): {sub_trans}")
                if merged_video and os.path.exists(merged_video): self.logger(f"[INFO] Merged Audio Video: {merged_video}")
            else:
                 self.logger("[WARN] Base filename was not determined, cannot list expected output files.")
            self.logger("[INFO] ---------------------------------------")
        else:
            self.logger("❌ Processing stopped due to an error. Please check the logs above.")

        return success