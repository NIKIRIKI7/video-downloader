# File: commands/translate_metadata.py

from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import get_tool_path
from deep_translator import GoogleTranslator
from pathlib import Path
import traceback

class TranslateMetadata(ActionCommand):
    """Команда для перевода метаданных (заголовок, описание, теги) на целевой язык."""

    def execute(self, context: ProcessingContext) -> None:
        """
        Переводит title, description и tags с source_lang на target_lang.
        Сохраняет переведённый файл с суффиксом ".meta.<lang>.txt".
        """
        if not context.base:
            self.log("[WARN] Нет базового имени, пропуск перевода метаданных.")
            return
        if not (context.title or context.description or context.tags):
            self.log("[INFO] Нет данных для перевода метаданных.")
            return

        src = context.source_lang
        tgt = context.target_lang
        if src == tgt:
            self.log(f"[WARN] Языки совпадают ({src}), перевод пропущен.")
            return

        out_path: Path = context.get_metadata_filepath(lang=tgt)  # type: ignore
        if out_path and out_path.exists():
            context.translated_metadata_path = out_path
            self.log(f"[WARN] Переведённый файл метаданных уже существует: {out_path}")
            return

        self.log(f"[INFO] Перевод метаданных с '{src}' на '{tgt}'...")
        translator = GoogleTranslator(source=src, target=tgt)
        t_title = ''
        t_description = ''
        t_tags: list[str] = []

        try:
            if context.title:
                try:
                    t_title = translator.translate(context.title)
                except Exception as e:
                    self.log(f"[ERROR] Ошибка перевода title: {e}")
            if context.description:
                try:
                    t_description = translator.translate(context.description)
                except Exception as e:
                    self.log(f"[ERROR] Ошибка перевода description: {e}")
            for tag in context.tags:
                if not tag.strip():
                    continue
                try:
                    tr = translator.translate(tag)
                    if tr:
                        t_tags.append(tr)
                except Exception as e:
                    self.log(f"[ERROR] Ошибка перевода тега '{tag}': {e}")

            # Сохраняем файл, если есть хотя бы что-то
            if not (t_title or t_description or t_tags):
                self.log("[WARN] Нет переведённых данных, файл не будет сохранён.")
                return

            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, 'w', encoding='utf-8') as f:
                f.write(f"Title: {t_title}\n\n")
                f.write(f"Description:\n{t_description}\n\n")
                f.write(f"Tags: {', '.join(t_tags)}")
            context.translated_metadata_path = out_path
            self.log(f"[INFO] Переведённые метаданные сохранены: {out_path}")

        except Exception as e:
            self.log(f"[ERROR] Неожиданная ошибка в TranslateMetadata: {type(e).__name__} - {e}")
            self.log(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            raise
