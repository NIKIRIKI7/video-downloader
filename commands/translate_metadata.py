from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
import constants
from deep_translator import GoogleTranslator
import os
import time

class TranslateMetadata(ActionCommand):
    """Command to translate metadata fields."""

    def execute(self, context: ProcessingContext) -> None:
        """Translates title, description, and tags."""
        if not context.base:
            self.log("[WARN] Skipping metadata translation: 'base' filename not set.")
            return
        if not context.title and not context.description and not context.tags:
            self.log("[INFO] Skipping metadata translation: No metadata found in context.")
            return

        target_lang = constants.TARGET_LANG
        source_lang = constants.SOURCE_LANG
        target_path = context.get_metadata_filepath(lang=target_lang)

        if not target_path:
            self.log("[ERROR] Cannot determine target metadata file path.")
            return

        if os.path.exists(target_path):
             self.log(f"[WARN] Translated metadata file already exists: {target_path}. Skipping.")
             # Optionally load existing data into context if needed later?
             context.translated_metadata_path = target_path
             return

        self.log(f"[INFO] Translating metadata from {source_lang} to {target_lang}...")

        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            t_title = ""
            t_description = ""
            t_tags = []

            # Translate Title
            if context.title:
                try:
                    t_title = translator.translate(context.title)
                    self.log(f"[DEBUG] Translated Title: {t_title}")
                except Exception as e:
                    self.log(f"[ERROR] Failed to translate title: {e}")
            else:
                 self.log("[DEBUG] No title to translate.")


            # Translate Description
            if context.description:
                try:
                     # Translate in chunks if description is very long? (Googletrans might handle it)
                     t_description = translator.translate(context.description)
                     self.log("[DEBUG] Description translated (content not shown).")
                except Exception as e:
                    self.log(f"[ERROR] Failed to translate description: {e}")
            else:
                self.log("[DEBUG] No description to translate.")

            # Translate Tags
            if context.tags:
                self.log(f"[INFO] Translating {len(context.tags)} tags...")
                for i, tag in enumerate(context.tags):
                    if not tag.strip(): continue
                    try:
                        # time.sleep(0.05) # Optional delay
                        translated_tag = translator.translate(tag)
                        if translated_tag:
                            t_tags.append(translated_tag)
                            # self.log(f"[DEBUG] Tag {i+1}: '{tag}' -> '{translated_tag}'")
                        else:
                            self.log(f"[WARN] Translation returned empty for tag: '{tag}'")
                    except Exception as e:
                        self.log(f"[ERROR] Failed to translate tag '{tag}': {e}")
                        # time.sleep(0.5) # Optional longer delay after error
                self.log(f"[INFO] Finished translating tags. Success: {len(t_tags)}/{len(context.tags)}")
            else:
                self.log("[DEBUG] No tags to translate.")


            # Save translated metadata
            if t_title or t_description or t_tags:
                self.log(f"[INFO] Saving translated metadata to: {target_path}")
                try:
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(f"Title: {t_title}\n\n")
                        f.write(f"Description:\n{t_description}\n\n")
                        f.write(f"Tags: {', '.join(t_tags)}")

                    context.translated_metadata_path = target_path
                    # Store translated fields in context too?
                    # context.translated_title = t_title
                    # context.translated_description = t_description
                    # context.translated_tags = t_tags
                    self.log("[INFO] Translated metadata saved successfully.")
                except IOError as e:
                    self.log(f"[ERROR] Failed to write translated metadata file {target_path}: {e}")
                    # raise?

            else:
                 self.log("[WARN] No metadata was successfully translated. Output file not saved.")

        except Exception as e:
            self.log(f"[ERROR] Unexpected error during metadata translation: {type(e).__name__} - {e}")
            import traceback
            self.log(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            raise