from commands.base_command import ActionCommand, LoggerCallable
from commands.download_video import DownloadVideo
from commands.download_subtitles import DownloadSubtitles
from commands.translate_subtitles import TranslateSubtitles
from commands.download_metadata import DownloadMetadata
from commands.translate_metadata import TranslateMetadata
from commands.merge_audio import MergeAudio
from commands.download_thumbnail import DownloadThumbnail # Добавлено
from model.processing_context import ProcessingContext
from utils.utils import find_executable, get_tool_path
import constants
import os
import subprocess # For specific exception handling
from typing import List, Dict, Any, Optional, Type

class VideoService:
    """
    Сервис, оркеструющий операции обработки видео с использованием команд и контекста.
    """
    COMMAND_MAPPING: Dict[str, Type[ActionCommand]] = {
        'md': DownloadMetadata,
        'dv': DownloadVideo,
        'ds': DownloadSubtitles,
        'dt': TranslateSubtitles,
        'da': MergeAudio,
        'tm': TranslateMetadata,
        'tp': DownloadThumbnail, # Добавлено: Действие для скачивания превью
    }

    # Зависимости: команды, требующие, чтобы 'md' (DownloadMetadata) был выполнен первым
    # для установки базового имени файла 'base' в контексте.
    METADATA_DEPENDENCIES = {'dv', 'ds', 'dt', 'da', 'tm', 'tp'} # 'tp' добавлен

    # Зависимости от инструментов для действий
    TOOL_DEPENDENCIES: Dict[str, List[str]] = {
        'md': ['yt-dlp'],
        'dv': ['yt-dlp', 'ffmpeg'], # ffmpeg часто нужен yt-dlp для слияния форматов
        'ds': ['yt-dlp'],
        'dt': [], # Требует deep_translator, pysubs2 (Python libs)
        'da': ['ffmpeg'],
        'tm': [], # Требует deep_translator (Python lib)
        'tp': ['yt-dlp'], # Добавлено
    }

    def __init__(self, logger: LoggerCallable):
        """
        Инициализирует сервис.

        Args:
            logger: Функция для логирования сообщений.
        """
        self.logger: LoggerCallable = logger

    def _check_tool_availability(self, actions: List[str]) -> bool:
        """Проверяет доступность необходимых внешних инструментов для выбранных действий."""
        required_tools = set()
        for action in actions:
            required_tools.update(self.TOOL_DEPENDENCIES.get(action, []))

        if not required_tools:
             self.logger("[DEBUG] Внешние инструменты не требуются для выбранных действий.")
             return True

        self.logger(f"[DEBUG] Проверка доступности инструментов: {required_tools}")
        all_tools_found = True
        for tool in required_tools:
             path_const_name = f"{tool.upper()}_PATH"
             configured_path = getattr(constants, path_const_name, None)

             if not find_executable(tool, configured_path):
                 self.logger(f"[ERROR] Необходимый инструмент '{tool}' не найден.")
                 self.logger(f"[ERROR] Пожалуйста, установите '{tool}' и убедитесь, что он в системном PATH,")
                 self.logger(f"[ERROR] или укажите полный путь в constants.py (переменная: {path_const_name}).")
                 all_tools_found = False
             else:
                  pass

        return all_tools_found


    def perform_actions(self, url: str, yandex_audio: Optional[str], actions: List[str], output_dir: str, settings: Dict[str, Any]) -> bool:
        """
        Выполняет запрошенные действия с использованием предоставленных настроек, заполняя ProcessingContext.

        Args:
            url: URL видео.
            yandex_audio: Путь к внешнему аудиофайлу (опционально, используется, если 'da' в actions).
            actions: Список ключей действий (например, ['md', 'dv', 'da']).
            output_dir: Директория для сохранения выходных файлов.
            settings: Словарь с конфигурацией от GUI/вызывающего кода
                      (например, {'source_lang': 'en', 'target_lang': 'ru', ...})

        Returns:
            True, если все запрошенные действия завершились успешно без критических ошибок, иначе False.
        """
        self.logger(f"[INFO] === Начало обработки видео ===")
        self.logger(f"[INFO] URL: {url}")
        self.logger(f"[INFO] Директория вывода: {output_dir}")
        self.logger(f"[INFO] Запрошенные действия: {actions}")
        self.logger(f"[INFO] Настройки: Языки({settings.get('source_lang')}>{settings.get('target_lang')}), Субтитры({settings.get('subtitle_lang')}/{settings.get('subtitle_format')}), Видео({settings.get('video_format_ext')}), Громкость({settings.get('original_volume')}/{settings.get('added_volume')})")

        # 1. Проверка доступности инструментов
        if not self._check_tool_availability(actions):
             self.logger("[ERROR] Прерывание обработки из-за отсутствия необходимых внешних инструментов.")
             return False

        # 2. Подготовка ProcessingContext
        try:
            context = ProcessingContext(
                url=url,
                yandex_audio=yandex_audio,
                output_dir=output_dir,
                **settings # Распаковка словаря настроек напрямую в поля контекста
            )
            self.logger(f"[DEBUG] ProcessingContext инициализирован: {context}")
        except TypeError as e:
             self.logger(f"[ERROR] Не удалось инициализировать ProcessingContext с предоставленными настройками: {e}")
             self.logger(f"[DEBUG] Предоставленные настройки: {settings}")
             return False

        # 3. Определение порядка выполнения: 'md' первым, если необходимо
        ordered_actions = actions[:]
        needs_metadata = any(action in self.METADATA_DEPENDENCIES for action in ordered_actions)

        if needs_metadata:
            if 'md' not in ordered_actions:
                ordered_actions.insert(0, 'md')
                self.logger("[INFO] Действие 'md' (Скачать метаданные) добавлено, так как оно требуется другими выбранными действиями.")
            elif ordered_actions.index('md') != 0:
                ordered_actions.remove('md')
                ordered_actions.insert(0, 'md')
                self.logger("[INFO] Действие 'md' (Скачать метаданные) перемещено в начало, так как это необходимое условие.")
        else:
             pass

        self.logger(f"[INFO] Итоговый порядок выполнения: {ordered_actions}")


        # 4. Последовательное выполнение команд
        success = True
        for action_key in ordered_actions:
            command_class = self.COMMAND_MAPPING.get(action_key)
            if not command_class:
                self.logger(f"[WARN] Неизвестный ключ действия '{action_key}', пропуск.")
                continue

            command_instance = command_class(self.logger)
            action_name = command_instance.__class__.__name__
            self.logger(f"--- ▶ Выполнение: {action_name} ---")

            try:
                # Проверка предварительных условий: зависит ли это действие от метаданных?
                if action_key in self.METADATA_DEPENDENCIES:
                    if context.base is None:
                        self.logger(f"[ERROR] Невозможно выполнить '{action_name}': Требуемое имя файла 'base' отсутствует в контексте.")
                        self.logger("[ERROR] Убедитесь, что действие 'md' (Скачать метаданные) выполняется успешно первым.")
                        success = False
                        break # Прекратить цепочку обработки

                # Выполнение действия команды
                command_instance.execute(context)
                self.logger(f"--- ✔ Завершено: {action_name} ---")

            # Обработка ожидаемых исключений
            except FileNotFoundError as e:
                self.logger(f"✖ ФАЙЛ/ИНСТРУМЕНТ НЕ НАЙДЕН во время {action_name}: {e}")
                success = False
                break
            except subprocess.CalledProcessError as e:
                self.logger(f"✖ ВНЕШНИЙ ИНСТРУМЕНТ ЗАВЕРШИЛСЯ С ОШИБКОЙ во время {action_name} (Код выхода: {e.returncode}). Проверьте логи выше для деталей.")
                success = False
                break
            except ValueError as e:
                self.logger(f"✖ ОШИБКА КОНФИГУРАЦИИ/ЗНАЧЕНИЯ во время {action_name}: {e}")
                success = False
                break
            except IOError as e:
                 self.logger(f"✖ ОШИБКА ВВОДА/ВЫВОДА ФАЙЛА во время {action_name}: {e}")
                 success = False
                 break
            except Exception as e:
                self.logger(f"✖ НЕОЖИДАННАЯ ОШИБКА во время {action_name}: {type(e).__name__} - {e}")
                import traceback
                self.logger(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
                success = False
                break

        # 5. Финальный отчет о статусе
        self.logger(f"[INFO] === Обработка {'Завершена' if success else 'Остановлена'} ===")
        if success:
            self.logger("🎉 Все выбранные действия успешно завершены.")
            self.logger("[INFO] --- Сгенерированные файлы (Проверьте наличие) ---")
            if context.base:
                meta_orig = context.get_metadata_filepath(lang=None)
                meta_trans = context.get_metadata_filepath(lang=context.target_lang)
                video_file = context.get_video_filepath()
                sub_orig = context.get_subtitle_filepath(lang=context.subtitle_lang)
                sub_trans = context.get_subtitle_filepath(lang=context.target_lang)
                merged_video = context.get_merged_video_filepath()
                thumbnail_file = context.get_thumbnail_filepath() # Добавлено

                if meta_orig and os.path.exists(meta_orig): self.logger(f"[INFO] Метаданные (Оригинал): {meta_orig}")
                if meta_trans and os.path.exists(meta_trans): self.logger(f"[INFO] Метаданные ({context.target_lang}): {meta_trans}")
                if video_file and os.path.exists(video_file): self.logger(f"[INFO] Видео ({context.video_format_ext}): {video_file}")
                if sub_orig and os.path.exists(sub_orig): self.logger(f"[INFO] Субтитры ({context.subtitle_lang}, {context.subtitle_format}): {sub_orig}")
                if sub_trans and os.path.exists(sub_trans): self.logger(f"[INFO] Субтитры ({context.target_lang}, {context.subtitle_format}): {sub_trans}")
                if merged_video and os.path.exists(merged_video): self.logger(f"[INFO] Видео со смешанным аудио: {merged_video}")
                if thumbnail_file and os.path.exists(thumbnail_file): self.logger(f"[INFO] Превью видео: {thumbnail_file}") # Добавлено
            else:
                 self.logger("[WARN] Базовое имя файла не было определено, невозможно перечислить ожидаемые выходные файлы.")
            self.logger("[INFO] ---------------------------------------")
        else:
            self.logger("❌ Обработка остановлена из-за ошибки. Пожалуйста, проверьте логи выше.")

        return success