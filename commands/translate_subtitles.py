from commands.base_command import ActionCommand
from model.processing_context import ProcessingContext
import pysubs2
from deep_translator import GoogleTranslator
import os
import time
import traceback

class TranslateSubtitles(ActionCommand):
    """Команда для перевода файлов субтитров на основе настроек контекста."""

    def execute(self, context: ProcessingContext) -> None:
        """Переводит субтитры, используя языки и формат из контекста."""
        if not context.subtitle_path:
            self.log("[WARN] Пропуск перевода субтитров: Путь к исходным субтитрам не найден в контексте (действие 'Скачать субтитры' было успешным?).")
            return
        if not os.path.exists(context.subtitle_path):
             self.log(f"[ERROR] Пропуск перевода субтитров: Исходный файл не найден: {context.subtitle_path}")
             raise FileNotFoundError(f"Исходный файл субтитров не найден: {context.subtitle_path}")

        if not context.base:
             self.log("[ERROR] Пропуск перевода субтитров: Базовое имя файла не установлено.")
             raise ValueError("Базовое имя файла не установлено в контексте для перевода субтитров.")

        source_path = context.subtitle_path
        target_lang = context.target_lang
        source_lang = context.source_lang
        target_format = context.subtitle_format

        if not source_lang or not target_lang:
             self.log("[ERROR] Исходный или Целевой язык отсутствует в контексте для перевода субтитров.")
             raise ValueError("Требуются Исходный и Целевой языки для перевода субтитров.")
        if not target_format:
            self.log("[ERROR] Формат субтитров отсутствует в контексте для перевода субтитров.")
            raise ValueError("Требуется формат субтитров для сохранения переведенных субтитров.")

        if source_lang == target_lang:
            self.log(f"[WARN] Исходный язык ('{source_lang}') и целевой язык ('{target_lang}') совпадают. Пропуск перевода субтитров.")
            return

        target_path = context.get_subtitle_filepath(target_lang)
        if not target_path:
            self.log("[ERROR] Невозможно определить путь к целевому файлу субтитров.")
            raise ValueError("Не удалось определить путь к целевому файлу субтитров.")

        if os.path.exists(target_path):
             self.log(f"[WARN] Переведенный файл субтитров уже существует: {target_path}. Пропуск перевода.")
             context.translated_subtitle_path = target_path
             return

        self.log(f"[INFO] Перевод субтитров с '{source_lang}' на '{target_lang}'...")
        self.log(f"[DEBUG] Источник: {source_path}")
        self.log(f"[DEBUG] Цель: {target_path} (Формат: {target_format})")

        try:
            self.log("[INFO] Загрузка исходных субтитров...")
            subs = pysubs2.load(source_path, encoding="utf-8")
            if not subs:
                self.log("[WARN] Исходный файл субтитров пуст или не может быть загружен pysubs2. Пропуск перевода.")
                return

            translator = GoogleTranslator(source=source_lang, target=target_lang)
            total_lines = len(subs)
            translated_count = 0
            error_count = 0
            empty_translation_count = 0

            self.log(f"[INFO] Начало перевода {total_lines} событий субтитров...")
            for i, line in enumerate(subs):
                if line.is_comment or not line.text or not line.text.strip():
                    continue

                original_text = line.text.replace('\\N', ' ').replace('\n', ' ').strip()
                if not original_text:
                     continue

                try:
                    # time.sleep(0.05) # Опциональная задержка
                    translated_text = translator.translate(original_text)

                    if translated_text and translated_text.strip():
                        line.text = translated_text.strip()
                        translated_count += 1
                        if (translated_count) % 50 == 0:
                            self.log(f"[DEBUG] Переведено строк: {translated_count}/{total_lines} (Событие {i+1})")
                    else:
                        self.log(f"[WARN] Перевод вернул пустое значение для строки {i+1}: '{original_text[:50]}...'")
                        empty_translation_count += 1
                        # Оставить оригинальный текст или очистить? Оставляем для безопасности.
                        # line.text = ""

                except Exception as e:
                    self.log(f"[ERROR] Не удалось перевести строку {i+1}: '{original_text[:50]}...' - {type(e).__name__}: {e}")
                    error_count += 1
                    # time.sleep(0.5) # Опциональная пауза после ошибки?

            self.log(f"[INFO] Перевод завершен. Успешно переведено: {translated_count}, Пустых переводов: {empty_translation_count}, Ошибок: {error_count}, Всего обработано событий: {total_lines}")

            if translated_count > 0:
                self.log(f"[INFO] Сохранение переведенных субтитров в: {target_path}")
                try:
                     subs.save(target_path, encoding="utf-8", format_=target_format)
                     context.translated_subtitle_path = target_path
                     self.log("[INFO] Переведенные субтитры успешно сохранены.")
                except Exception as save_e:
                     self.log(f"[ERROR] Не удалось сохранить переведенные субтитры в {target_path}: {save_e}")
                     raise IOError(f"Не удалось сохранить переведенные субтитры: {save_e}")
            else:
                 self.log("[WARN] Ни одна строка не была успешно переведена. Выходной файл не сохранен.")

        except FileNotFoundError:
            self.log(f"[ERROR] Исходный файл субтитров не найден во время загрузки перевода: {source_path}")
            raise
        except Exception as e:
            self.log(f"[ERROR] Неожиданная ошибка во время перевода субтитров: {type(e).__name__} - {e}")
            self.log(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
            raise