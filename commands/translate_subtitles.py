from commands.base_command import ActionCommand
from constants import VIDEO_DIR
import pysubs2
from deep_translator import GoogleTranslator
import os
from typing import Dict, Any

class TranslateSubtitles(ActionCommand):
    """Команда для перевода файла субтитров VTT с английского на русский."""

    TARGET_LANG = "ru"
    SOURCE_LANG = "en"

    def execute(self, context: Dict[str, Any]) -> None:
        """
        Переводит файл субтитров, указанный в context['subtitle_path'].

        Args:
            context: Словарь контекста. Ожидает 'base' и 'subtitle_path'.
                     Обновляет 'translated_subtitle_path'.

        Raises:
            KeyError: Если в контексте отсутствуют 'base' или 'subtitle_path'.
            FileNotFoundError: Если файл субтитров context['subtitle_path'] не найден.
            Exception: Если произошла ошибка во время перевода или сохранения файла.
        """
        if 'subtitle_path' not in context or not context['subtitle_path']:
            self.log("Пропуск перевода субтитров: путь к исходным субтитрам не найден в контексте.")
            return # Не можем продолжить без исходного файла

        base = context['base'] # Нужен для имени выходного файла
        source_path = context['subtitle_path']
        target_filename = f"{base}.{self.TARGET_LANG}.vtt"
        target_path = os.path.join(VIDEO_DIR, target_filename)

        self.log(f"Перевод субтитров из {source_path} в {target_path}")

        try:
            # Загрузка субтитров
            self.log("Загрузка исходных субтитров...")
            subs = pysubs2.load(source_path, encoding="utf-8")
            if not subs:
                 self.log("Файл субтитров пуст или не удалось загрузить.")
                 return # Нечего переводить

            # Инициализация переводчика
            translator = GoogleTranslator(source=self.SOURCE_LANG, target=self.TARGET_LANG)

            self.log("Начало перевода строк...")
            translated_count = 0
            # Перевод каждой строки
            # Обернем в try-except на случай проблем с отдельными строками или API
            for i, line in enumerate(subs):
                if line.is_comment or not line.text:
                    continue # Пропускаем комментарии и пустые строки

                try:
                    # Заменяем разрывы строк, которые могут мешать переводу
                    original_text = line.text.replace('\n', ' ').replace('\\N', ' ')
                    translated_text = translator.translate(original_text)
                    if translated_text:
                        line.text = translated_text
                        translated_count += 1
                    else:
                        self.log(f"Предупреждение: Перевод строки {i+1} вернул пустой результат.")
                except Exception as e:
                    self.log(f"Ошибка перевода строки {i+1}: '{line.text[:50]}...' - {e}")
                    # Решаем, прерывать ли весь процесс или пропустить строку
                    # Пока пропускаем
                    continue

            self.log(f"Переведено строк: {translated_count} из {len(subs)}")

            # Сохранение переведенных субтитров
            if translated_count > 0:
                self.log(f"Сохранение переведенных субтитров в {target_path}")
                subs.save(target_path, encoding="utf-8", format_="vtt")
                context['translated_subtitle_path'] = target_path
                self.log("Переведенные субтитры успешно сохранены.")
            else:
                self.log("Перевод субтитров не выполнен (нет строк для перевода или все строки вызвали ошибки).")


        except FileNotFoundError:
            self.log(f"Ошибка: Исходный файл субтитров не найден: {source_path}")
            raise # Передаем ошибку выше
        except Exception as e:
            # Ловим другие возможные ошибки (от deep_translator, pysubs2, IO)
            self.log(f"Ошибка во время перевода или сохранения субтитров: {e}")
            raise