# File: commands/translate_subtitles.py

from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from utils.utils import get_tool_path, is_valid_time_format
from deep_translator import GoogleTranslator
import pysubs2
from pathlib import Path
import traceback

class TranslateSubtitles(ActionCommand):
    """Команда для перевода субтитров (файл .vtt/.srt) на целевой язык."""

    def execute(self, context: ProcessingContext) -> None:
        """
        Переводит субтитры из context.subtitle_path в target_lang,
        сохраняет в context.translated_subtitle_path.
        """
        src_path: Path = context.subtitle_path  # type: ignore
        if not src_path or not src_path.exists():
            self.log(f"[WARN] Исходный файл субтитров не найден: {src_path}")
            return
        if not context.base:
            raise ValueError("Не задано базовое имя для перевода субтитров.")

        src_lang = context.source_lang
        tgt_lang = context.target_lang
        fmt = context.subtitle_format
        if src_lang == tgt_lang:
            self.log(f"[WARN] Языки совпадают ({src_lang}), перевод субтитров пропущен.")
            return
        if not fmt:
            raise ValueError("Не указан формат субтитров для сохранения.")

        out_path: Path = context.get_subtitle_filepath(tgt_lang)  # type: ignore
        if out_path and out_path.exists():
            context.translated_subtitle_path = out_path
            self.log(f"[WARN] Переведённый файл субтитров уже существует: {out_path}")
            return

        self.log(f"[INFO] Загрузка субтитров для перевода: {src_path}")
        try:
            subs = pysubs2.load(str(src_path), encoding="utf-8")
        except Exception as e:
            self.log(f"[ERROR] Ошибка загрузки субтитров: {e}")
            raise

        translator = GoogleTranslator(source=src_lang, target=tgt_lang)
        total = len(subs)
        translated = 0

        for event in subs:
            text = event.text.strip()
            if not text or event.is_comment:
                continue
            try:
                tr = translator.translate(text.replace('\\N', ' '))
                event.text = tr.replace('\n', '\\N')
                translated += 1
                if translated % 50 == 0:
                    self.log(f"[DEBUG] Переведено {translated}/{total} строк...")
            except Exception as e:
                self.log(f"[ERROR] Ошибка перевода строки '{text[:30]}...': {e}")

        if translated == 0:
            self.log("[WARN] Не удалось перевести ни одной строки субтитров.")
            return

        # Сохраняем результат
        out_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            subs.save(str(out_path), encoding="utf-8", format_=fmt)
            context.translated_subtitle_path = out_path
            self.log(f"[INFO] Переведённые субтитры сохранены: {out_path}")
        except Exception as e:
            self.log(f"[ERROR] Ошибка сохранения переведённых субтитров: {e}")
            self.log(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            raise
