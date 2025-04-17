from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
import constants
import pysubs2
from deep_translator import GoogleTranslator
import os
import time

class TranslateSubtitles(ActionCommand):
    """Command to translate subtitle files."""

    def execute(self, context: ProcessingContext) -> None:
        """Translates subtitles from source_path to target_path."""
        if not context.subtitle_path:
            self.log("[WARN] Skipping subtitle translation: No source subtitle path found in context.")
            return
        if not os.path.exists(context.subtitle_path):
             self.log(f"[ERROR] Skipping subtitle translation: Source file not found: {context.subtitle_path}")
             return # Cannot proceed without source file

        if not context.base:
             self.log("[ERROR] Skipping subtitle translation: Base filename not set.")
             return

        source_path = context.subtitle_path
        target_lang = constants.TARGET_LANG
        source_lang = constants.SOURCE_LANG
        target_path = context.get_subtitle_filepath(target_lang)

        if not target_path:
            self.log("[ERROR] Cannot determine target subtitle file path.")
            return

        if os.path.exists(target_path):
             self.log(f"[WARN] Translated subtitle file already exists: {target_path}. Skipping translation.")
             context.translated_subtitle_path = target_path
             return

        self.log(f"[INFO] Translating subtitles from {source_lang} to {target_lang}...")
        self.log(f"[DEBUG] Source: {source_path}")
        self.log(f"[DEBUG] Target: {target_path}")

        try:
            self.log("[INFO] Loading source subtitles...")
            subs = pysubs2.load(source_path, encoding="utf-8")
            if not subs:
                self.log("[WARN] Source subtitle file is empty or failed to load.")
                return

            translator = GoogleTranslator(source=source_lang, target=target_lang)
            total_lines = len(subs)
            translated_count = 0
            error_count = 0

            self.log(f"[INFO] Starting translation of {total_lines} lines...")
            for i, line in enumerate(subs):
                if line.is_comment or not line.text.strip():
                    continue # Skip comments and empty lines

                original_text = line.text.replace('\n', ' ').replace('\\N', ' ') # Clean text for translator
                try:
                    # Add small delay to potentially avoid API rate limits
                    # time.sleep(0.05) # Adjust delay as needed or remove
                    translated_text = translator.translate(original_text)

                    if translated_text:
                        line.text = translated_text
                        translated_count += 1
                        # Log progress periodically
                        if (i + 1) % 50 == 0:
                            self.log(f"[DEBUG] Translated line {i+1}/{total_lines}")
                    else:
                        self.log(f"[WARN] Translation returned empty for line {i+1}: '{original_text[:50]}...'")
                        error_count += 1

                except Exception as e:
                    self.log(f"[ERROR] Failed to translate line {i+1}: '{original_text[:50]}...' - {type(e).__name__}: {e}")
                    error_count += 1
                    # Decide whether to continue or stop
                    # time.sleep(0.5) # Longer pause after error?

            self.log(f"[INFO] Translation finished. Translated: {translated_count}, Errors/Skipped: {error_count}, Total: {total_lines}")

            if translated_count > 0:
                self.log(f"[INFO] Saving translated subtitles to: {target_path}")
                try:
                     subs.save(target_path, encoding="utf-8", format_=constants.SUB_FORMAT)
                     context.translated_subtitle_path = target_path
                     self.log("[INFO] Translated subtitles saved successfully.")
                except Exception as save_e:
                     self.log(f"[ERROR] Failed to save translated subtitles to {target_path}: {save_e}")
                     # Don't raise, but log the failure
            else:
                 self.log("[WARN] No lines were successfully translated. Output file not saved.")


        except FileNotFoundError:
            # This should be caught earlier, but handle defensively
            self.log(f"[ERROR] Source subtitle file not found during translation: {source_path}")
            raise
        except Exception as e:
            self.log(f"[ERROR] Unexpected error during subtitle translation: {type(e).__name__} - {e}")
            import traceback
            self.log(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            raise # Re-raise unexpected errors