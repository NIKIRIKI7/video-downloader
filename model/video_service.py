from commands.base_command import ActionCommand, LoggerCallable
from commands.download_video import DownloadVideo
from commands.download_subtitles import DownloadSubtitles
from commands.translate_subtitles import TranslateSubtitles
from commands.download_metadata import DownloadMetadata
# Команда TranslateMetadata не используется напрямую через чекбоксы, но может быть добавлена
# from commands.translate_metadata import TranslateMetadata
from commands.merge_audio import MergeAudio
from typing import List, Dict, Any, Optional, Type

class VideoService:
    """
    Сервис для выполнения последовательности операций над видео.
    Использует паттерн Команда для выполнения действий.
    """
    # Словарь для маппинга ключей действий на классы команд
    COMMAND_MAPPING: Dict[str, Type[ActionCommand]] = {
        'dv': DownloadVideo,
        'ds': DownloadSubtitles,
        'dt': TranslateSubtitles,
        'md': DownloadMetadata,
        'da': MergeAudio,
        # 'tm': TranslateMetadata, # Пример добавления команды перевода метаданных
    }

    # Определяем зависимости: какие команды требуют выполнения 'md' (DownloadMetadata) перед собой
    METADATA_DEPENDENCIES = {'dv', 'ds', 'dt', 'da'} # 'tm' тоже будет зависеть

    def __init__(self, logger: LoggerCallable):
        """
        Инициализатор сервиса.

        Args:
            logger: Функция для логирования сообщений.
        """
        self.logger: LoggerCallable = logger

    def perform_actions(self, url: str, yandex_audio: Optional[str], actions: List[str]) -> bool:
        """
        Выполняет запрошенные действия в определенном порядке.

        Args:
            url: URL видео.
            yandex_audio: Путь к файлу Yandex Audio (если используется).
            actions: Список ключей действий для выполнения (например, ['md', 'dv', 'da']).

        Returns:
            True, если все запрошенные действия выполнены успешно, False в противном случае.
        """
        context: Dict[str, Any] = {"url": url, "yandex_audio": yandex_audio, "base": None}

        # Убедимся, что метаданные загружаются первыми, если они нужны другим командам
        ordered_actions = actions[:] # Копируем список
        needs_metadata = any(action in self.METADATA_DEPENDENCIES for action in ordered_actions)

        if needs_metadata and 'md' not in ordered_actions:
            # Если нужны метаданные, но команда 'md' не выбрана, добавляем ее в начало
            ordered_actions.insert(0, 'md')
            self.logger("Примечание: Добавлено действие 'Download Metadata', так как оно необходимо для других выбранных действий.")
        elif 'md' in ordered_actions and ordered_actions[0] != 'md':
            # Если 'md' выбрана, но не первая, перемещаем ее в начало
            ordered_actions.remove('md')
            ordered_actions.insert(0, 'md')
            self.logger("Примечание: Действие 'Download Metadata' будет выполнено первым.")


        self.logger(f"Начало выполнения действий для URL: {url}")
        self.logger(f"Запрошенные действия: {actions}")
        self.logger(f"Порядок выполнения: {ordered_actions}")

        success = True
        for action_key in ordered_actions:
            command_class = self.COMMAND_MAPPING.get(action_key)
            if command_class:
                command_instance = command_class(self.logger)
                action_name = command_instance.__class__.__name__
                self.logger(f"▶ Выполнение: {action_name}...")
                try:
                    # Проверяем предусловия перед выполнением команды (пример)
                    if action_key in self.METADATA_DEPENDENCIES and context.get('base') is None:
                         # Это не должно произойти из-за логики выше, но для страховки
                         self.logger(f"Ошибка: Не удалось выполнить '{action_name}', т.к. отсутствуют метаданные ('base').")
                         success = False
                         break # Прерываем выполнение цепочки

                    # Выполняем команду
                    command_instance.execute(context)
                    self.logger(f"✔ Завершено: {action_name}.")

                except KeyError as e:
                    self.logger(f"✖ Ошибка конфигурации для {action_name}: отсутствует необходимый ключ в контексте: {e}")
                    success = False
                    break # Прерываем выполнение
                except FileNotFoundError as e:
                    self.logger(f"✖ Ошибка файла для {action_name}: {e}")
                    # Часто это означает, что не найдены внешние утилиты (yt-dlp, ffmpeg) или входные файлы
                    success = False
                    break # Прерываем выполнение
                except subprocess.CalledProcessError as e:
                    self.logger(f"✖ Ошибка внешней команды для {action_name}: {e}")
                    # Лог ошибки уже должен быть внутри команды, здесь просто фиксируем факт
                    success = False
                    break # Прерываем выполнение
                except Exception as e:
                    # Ловим все остальные непредвиденные ошибки
                    self.logger(f"✖ Неожиданная ошибка при выполнении {action_name}: {type(e).__name__} - {e}")
                    import traceback
                    self.logger(f"Traceback:\n{traceback.format_exc()}")
                    success = False
                    break # Прерываем выполнение
            else:
                self.logger(f"Предупреждение: Неизвестный ключ действия '{action_key}', пропуск.")

        if success:
            self.logger("🎉 Все запрошенные действия успешно завершены.")
        else:
            self.logger("❌ Выполнение прервано из-за ошибки.")

        return success