from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
from deep_translator import GoogleTranslator
import os
import time
import traceback

class TranslateMetadata(ActionCommand):
    """Команда для перевода полей метаданных на основе настроек контекста."""

    def execute(self, context: ProcessingContext) -> None:
        """Переводит заголовок, описание и теги, используя языки из контекста."""
        if not context.base:
            self.log("[WARN] Пропуск перевода метаданных: базовое имя файла 'base' не установлено.")
            return
        if not context.title and not context.description and not context.tags:
            self.log("[INFO] Пропуск перевода метаданных: Исходные метаданные (заголовок, описание, теги) не найдены в контексте.")
            return

        target_lang = context.target_lang
        source_lang = context.source_lang

        if not source_lang or not target_lang:
             self.log("[ERROR] Исходный или Целевой язык отсутствует в контексте для перевода метаданных.")
             raise ValueError("Требуются Исходный и Целевой языки для перевода.")
        if source_lang == target_lang:
             self.log(f"[WARN] Исходный язык ('{source_lang}') и целевой язык ('{target_lang}') совпадают. Пропуск перевода метаданных.")
             return

        target_path = context.get_metadata_filepath(lang=target_lang)
        if not target_path:
            self.log("[ERROR] Невозможно определить путь к целевому файлу метаданных.")
            raise ValueError("Не удалось определить путь к целевому файлу метаданных.")

        if os.path.exists(target_path):
             self.log(f"[WARN] Переведенный файл метаданных уже существует: {target_path}. Пропуск перевода.")
             context.translated_metadata_path = target_path
             return

        self.log(f"[INFO] Перевод метаданных с '{source_lang}' на '{target_lang}'...")

        try:
            translator = GoogleTranslator(source=source_lang, target=target_lang)
            t_title = ""
            t_description = ""
            t_tags = []

            if context.title:
                self.log("[DEBUG] Перевод заголовка...")
                try:
                    t_title = translator.translate(context.title)
                    self.log(f"[DEBUG] Переведенный заголовок: {t_title}")
                except Exception as e:
                    self.log(f"[ERROR] Не удалось перевести заголовок: {e}")

            if context.description:
                 self.log("[DEBUG] Перевод описания...")
                 try:
                     t_description = translator.translate(context.description)
                     self.log("[DEBUG] Описание переведено (содержимое не показано).")
                 except Exception as e:
                     self.log(f"[ERROR] Не удалось перевести описание: {e}")

            if context.tags:
                self.log(f"[INFO] Перевод {len(context.tags)} тегов...")
                for i, tag in enumerate(context.tags):
                    if not tag or not tag.strip():
                        self.log(f"[DEBUG] Пропуск пустого тега с индексом {i}.")
                        continue
                    try:
                        # time.sleep(0.05) # Опциональная небольшая задержка
                        translated_tag = translator.translate(tag)
                        if translated_tag:
                            t_tags.append(translated_tag)
                        else:
                            self.log(f"[WARN] Перевод вернул пустое значение для тега: '{tag}'")
                    except Exception as e:
                        self.log(f"[ERROR] Не удалось перевести тег '{tag}': {e}")
                        # time.sleep(0.5) # Опциональная более длительная задержка после ошибки?
                self.log(f"[INFO] Завершен перевод тегов. Успешно/Попыток: {len(t_tags)}/{len(context.tags)}")

            if t_title or t_description or t_tags:
                self.log(f"[INFO] Сохранение переведенных метаданных в: {target_path}")
                try:
                    with open(target_path, 'w', encoding='utf-8') as f:
                        f.write(f"Title: {t_title if t_title else ''}\n\n")
                        f.write(f"Description:\n{t_description if t_description else ''}\n\n")
                        f.write(f"Tags: {', '.join(t_tags) if t_tags else ''}")

                    context.translated_metadata_path = target_path
                    self.log("[INFO] Переведенные метаданные успешно сохранены.")
                except IOError as e:
                    self.log(f"[ERROR] Не удалось записать переведенный файл метаданных {target_path}: {e}")
                    raise
            else:
                 self.log("[WARN] Метаданные не были успешно переведены (или исходные были пустыми). Выходной файл не сохранен.")

        except Exception as e:
            self.log(f"[ERROR] Неожиданная ошибка во время настройки или выполнения перевода метаданных: {type(e).__name__} - {e}")
            self.log(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            raise