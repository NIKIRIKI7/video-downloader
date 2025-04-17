from commands.base_command import ActionCommand
from constants import VIDEO_DIR
from deep_translator import GoogleTranslator
import os
from typing import Dict, Any, List

class TranslateMetadata(ActionCommand):
    """Команда для перевода метаданных (название, описание, теги) с английского на русский."""

    TARGET_LANG = "ru"
    SOURCE_LANG = "en"

    def execute(self, context: Dict[str, Any]) -> None:
        """
        Переводит метаданные, хранящиеся в контексте, и сохраняет их в файл .meta.ru.txt.

        Args:
            context: Словарь контекста. Ожидает 'base', 'title', 'description', 'tags'.
                     Обновляет 'translated_title', 'translated_description', 'translated_tags',
                     'translated_metadata_path'.

        Raises:
            KeyError: Если в контексте отсутствуют необходимые ключи.
            Exception: Если произошла ошибка во время перевода или сохранения файла.
        """
        if not all(key in context for key in ['base', 'title', 'description', 'tags']):
            self.log("Пропуск перевода метаданных: отсутствуют необходимые данные в контексте.")
            return

        base = context['base']
        title = context['title']
        description = context['description']
        tags = context.get('tags', []) # Используем get для безопасности, вдруг тегов нет

        # Проверка, есть ли что переводить
        if not title and not description and not tags:
            self.log("Пропуск перевода метаданных: нет текста для перевода.")
            return

        self.log("Перевод метаданных...")

        try:
            translator = GoogleTranslator(source=self.SOURCE_LANG, target=self.TARGET_LANG)

            # Перевод заголовка
            t_title = translator.translate(title) if title else ""
            self.log(f"Заголовок переведен: '{t_title}'")

            # Перевод описания (может быть длинным, переводим как есть)
            # Добавим проверку на None/пустоту перед переводом
            t_description = translator.translate(description) if description else ""
            self.log("Описание переведено.") # Не логгируем всё описание

            # Перевод тегов
            t_tags: List[str] = []
            if tags:
                self.log(f"Перевод {len(tags)} тегов...")
                for i, tag in enumerate(tags):
                    try:
                        if tag: # Проверяем, что тег не пустой
                           translated_tag = translator.translate(tag)
                           if translated_tag:
                               t_tags.append(translated_tag)
                        # Небольшая пауза между тегами может помочь избежать бана API
                        # time.sleep(0.1) # Раскомментировать при необходимости
                    except Exception as e:
                         self.log(f"Ошибка перевода тега '{tag}': {e}")
                         # Пропускаем ошибочный тег
                         continue
                self.log(f"Теги переведены: {', '.join(t_tags)}")
            else:
                 self.log("Теги для перевода отсутствуют.")


            # Сохранение переведенных метаданных
            output_filename = f"{base}.meta.{self.TARGET_LANG}.txt"
            output_path = os.path.join(VIDEO_DIR, output_filename)

            self.log(f"Сохранение переведенных метаданных в: {output_path}")
            try:
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(f"Title: {t_title}\n\n")
                    f.write(f"Description:\n{t_description}\n\n")
                    f.write(f"Tags: {', '.join(t_tags)}")

                # Сохраняем переведенные данные в контекст для возможного дальнейшего использования
                context['translated_title'] = t_title
                context['translated_description'] = t_description
                context['translated_tags'] = t_tags
                context['translated_metadata_path'] = output_path
                self.log("Переведенные метаданные успешно сохранены.")

            except IOError as e:
                self.log(f"Ошибка записи файла переведенных метаданных {output_path}: {e}")
                raise # Передаем ошибку выше

        except Exception as e:
            # Ловим другие возможные ошибки (от deep_translator)
            self.log(f"Ошибка во время перевода метаданных: {e}")
            raise