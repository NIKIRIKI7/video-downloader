from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from deep_translator import GoogleTranslator # Ensure this is installed
import os
import time # Keep for potential delays

class TranslateMetadata(ActionCommand):
    """Command to translate metadata fields based on context settings."""

    def execute(self, context: ProcessingContext) -> None:
        """Translates title, description, and tags using languages from context."""
        if not context.base:
            self.log("[WARN] Skipping metadata translation: 'base' filename not set.")
            return
        if not context.title and not context.description and not context.tags:
            self.log("[INFO] Skipping metadata translation: No source metadata (title, desc, tags) found in context.")
            return

        # Read settings from context
        target_lang = context.target_lang
        source_lang = context.source_lang

        if not source_lang or not target_lang:
             self.log("[ERROR] Source or Target language is missing in context for metadata translation.")
             raise ValueError("Source and Target languages are required for translation.")
        if source_lang == target_lang:
             self.log(f"[WARN] Source language ('{source_lang}') and target language ('{target_lang}') are the same. Skipping metadata translation.")
             return


        # Get target path using context method and target_lang
        target_path = context.get_metadata_filepath(lang=target_lang)

        if not target_path:
            self.log("[ERROR] Cannot determine target metadata file path.")
            # Raise error, as we can't save the result
            raise ValueError("Could not determine target metadata file path.")

        if os.path.exists(target_path):
             self.log(f"[WARN] Translated metadata file already exists: {target_path}. Skipping translation.")
             # Ensure context is aware of the existing file
             context.translated_metadata_path = target_path
             return

        self.log(f"[INFO] Translating metadata from '{source_lang}' to '{target_lang}'...")

        try:
            # Use languages from context
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            t_title = ""
            t_description = ""
            t_tags = []

            # Translate Title
            if context.title:
                self.log("[DEBUG] Translating title...")
                try:
                    t_title = translator.translate(context.title)
                    self.log(f"[DEBUG] Translated Title: {t_title}")
                except Exception as e:
                    self.log(f"[ERROR] Failed to translate title: {e}")
                    # Decide if this should be fatal? Maybe continue with other fields.
            else:
                 self.log("[DEBUG] No title to translate.")

            # Translate Description
            if context.description:
                 self.log("[DEBUG] Translating description...")
                 try:
                     # Consider chunking for very long descriptions if translator fails
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
                    if not tag or not tag.strip():
                        self.log(f"[DEBUG] Skipping empty tag at index {i}.")
                        continue
                    try:
                        # time.sleep(0.05) # Optional small delay
                        translated_tag = translator.translate(tag)
                        if translated_tag:
                            t_tags.append(translated_tag)
                            # self.log(f"[DEBUG] Tag {i+1}: '{tag}' -> '{translated_tag}'")
                        else:
                            # Log if translation returns empty, might be expected for some tags
                            self.log(f"[WARN] Translation returned empty for tag: '{tag}'")
                    except Exception as e:
                        # Log error for specific tag but continue with others
                        self.log(f"[ERROR] Failed to translate tag '{tag}': {e}")
                        # time.sleep(0.5) # Optional longer delay after error?
                self.log(f"[INFO] Finished translating tags. Success/Attempted: {len(t_tags)}/{len(context.tags)}")
            else:
                self.log("[DEBUG] No tags to translate.")

            # Save translated metadata only if something was translated
            if t_title or t_description or t_tags:
                self.log(f"[INFO] Saving translated metadata to: {target_path}")
                try:
                    with open(target_path, 'w', encoding='utf-8') as f:
                        # Ensure fields exist before writing
                        f.write(f"Title: {t_title if t_title else ''}\n\n")
                        f.write(f"Description:\n{t_description if t_description else ''}\n\n")
                        f.write(f"Tags: {', '.join(t_tags) if t_tags else ''}")

                    context.translated_metadata_path = target_path
                    # Optionally store translated fields in context too, if needed later
                    # context.translated_title = t_title
                    # context.translated_description = t_description
                    # context.translated_tags = t_tags
                    self.log("[INFO] Translated metadata saved successfully.")
                except IOError as e:
                    self.log(f"[ERROR] Failed to write translated metadata file {target_path}: {e}")
                    # Raise IO error as saving failed
                    raise
            else:
                 self.log("[WARN] No metadata was successfully translated (or source was empty). Output file not saved.")

        except Exception as e:
            # Catch errors from GoogleTranslator instantiation or other unexpected issues
            self.log(f"[ERROR] Unexpected error during metadata translation setup or execution: {type(e).__name__} - {e}")
            import traceback
            self.log(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            raise