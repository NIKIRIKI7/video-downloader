from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
import pysubs2 # Ensure this is installed
from deep_translator import GoogleTranslator # Ensure this is installed
import os
import time # Keep for potential delays

class TranslateSubtitles(ActionCommand):
    """Command to translate subtitle files based on context settings."""

    def execute(self, context: ProcessingContext) -> None:
        """Translates subtitles using languages and format from context."""
        if not context.subtitle_path:
            self.log("[WARN] Skipping subtitle translation: No source subtitle path found in context (was 'Download Subtitles' successful?).")
            return
        if not os.path.exists(context.subtitle_path):
             self.log(f"[ERROR] Skipping subtitle translation: Source file not found: {context.subtitle_path}")
             # Cannot proceed without the source file
             raise FileNotFoundError(f"Source subtitle file not found: {context.subtitle_path}")

        if not context.base:
             self.log("[ERROR] Skipping subtitle translation: Base filename not set.")
             raise ValueError("Base filename not set in context for subtitle translation.")

        source_path = context.subtitle_path
        # Read settings from context
        target_lang = context.target_lang
        source_lang = context.source_lang
        # Target format should typically be the same as the source format
        target_format = context.subtitle_format

        if not source_lang or not target_lang:
             self.log("[ERROR] Source or Target language is missing in context for subtitle translation.")
             raise ValueError("Source and Target languages are required for subtitle translation.")
        if not target_format:
            self.log("[ERROR] Subtitle format is missing in context for subtitle translation.")
            raise ValueError("Subtitle format is required for saving translated subtitles.")

        if source_lang == target_lang:
            self.log(f"[WARN] Source language ('{source_lang}') and target language ('{target_lang}') are the same. Skipping subtitle translation.")
            return

        # Get target path using context method and target_lang
        target_path = context.get_subtitle_filepath(target_lang)

        if not target_path:
            self.log("[ERROR] Cannot determine target subtitle file path.")
            raise ValueError("Could not determine target subtitle file path.")

        if os.path.exists(target_path):
             self.log(f"[WARN] Translated subtitle file already exists: {target_path}. Skipping translation.")
             context.translated_subtitle_path = target_path # Ensure context is aware
             return

        self.log(f"[INFO] Translating subtitles from '{source_lang}' to '{target_lang}'...")
        self.log(f"[DEBUG] Source: {source_path}")
        self.log(f"[DEBUG] Target: {target_path} (Format: {target_format})")

        try:
            self.log("[INFO] Loading source subtitles...")
            # Explicitly provide encoding, although pysubs2 often detects it
            subs = pysubs2.load(source_path, encoding="utf-8")
            if not subs:
                # This might happen if the file is empty or completely invalid
                self.log("[WARN] Source subtitle file is empty or could not be loaded by pysubs2. Skipping translation.")
                return

            # Use languages from context
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            total_lines = len(subs)
            translated_count = 0
            error_count = 0
            empty_translation_count = 0

            self.log(f"[INFO] Starting translation of {total_lines} subtitle events...")
            for i, line in enumerate(subs):
                # Process only dialogue events, skip comments and empty lines
                if line.is_comment or not line.text or not line.text.strip():
                    continue

                # Prepare text for translator (replace newlines, handle potential formatting)
                # Basic cleaning: replace SSA/ASS newlines (\N) and standard newlines
                original_text = line.text.replace('\\N', ' ').replace('\n', ' ').strip()
                if not original_text: # Skip if cleaning results in empty text
                     continue

                try:
                    # Optional delay to potentially avoid hitting API rate limits
                    # time.sleep(0.05) # Adjust delay as needed or remove if causing slowdown

                    translated_text = translator.translate(original_text)

                    if translated_text and translated_text.strip():
                        # Restore basic newline if needed, or keep as single line?
                        # For simplicity, keep as single line from translator for now.
                        # If original had \N, we might want to try and split/re-insert,
                        # but that adds complexity.
                        line.text = translated_text.strip()
                        translated_count += 1
                        # Log progress periodically
                        if (translated_count) % 50 == 0: # Log every 50 successful translations
                            self.log(f"[DEBUG] Translated lines: {translated_count}/{total_lines} (Event {i+1})")
                    else:
                        # Log when the translation service returns an empty/null response
                        self.log(f"[WARN] Translation returned empty for line {i+1}: '{original_text[:50]}...'")
                        empty_translation_count += 1
                        # Keep original text in this case? Or empty it? Keeping original seems safer.
                        # line.text = "" # Option: clear text if translation fails/is empty

                except Exception as e:
                    self.log(f"[ERROR] Failed to translate line {i+1}: '{original_text[:50]}...' - {type(e).__name__}: {e}")
                    error_count += 1
                    # Decide whether to continue or stop on error
                    # time.sleep(0.5) # Optional longer pause after error?

            self.log(f"[INFO] Translation finished. Successfully translated: {translated_count}, Empty translations: {empty_translation_count}, Errors: {error_count}, Total events processed: {total_lines}")

            # Save only if some lines were successfully translated
            if translated_count > 0:
                self.log(f"[INFO] Saving translated subtitles to: {target_path}")
                try:
                     # Save using the target format specified in context
                     subs.save(target_path, encoding="utf-8", format_=target_format)
                     context.translated_subtitle_path = target_path
                     self.log("[INFO] Translated subtitles saved successfully.")
                except Exception as save_e:
                     self.log(f"[ERROR] Failed to save translated subtitles to {target_path}: {save_e}")
                     # Raise the saving error, as the translation work might be lost
                     raise IOError(f"Failed to save translated subtitles: {save_e}")
            else:
                 self.log("[WARN] No lines were successfully translated. Output file not saved.")


        except FileNotFoundError:
            # This should have been caught before starting, but handle defensively
            self.log(f"[ERROR] Source subtitle file not found during translation load: {source_path}")
            raise # Re-raise as it's a prerequisite failure
        except Exception as e:
            # Catch errors from pysubs2 loading, GoogleTranslator instantiation, or other issues
            self.log(f"[ERROR] Unexpected error during subtitle translation: {type(e).__name__} - {e}")
            import traceback
            self.log(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            raise # Re-raise unexpected errors