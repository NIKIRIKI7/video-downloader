import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import os
import re # Для валидации URL и времени
import traceback

# Используем относительные импорты внутри пакета gui
from .process_tab import ProcessTab
from .settings_tab import SettingsTab
from .trim_tab import TrimTab # Добавлено

# Импортируем ViewModel и другие зависимости
from viewmodel.video_viewmodel import VideoViewModel
import constants
from utils.utils import find_executable, is_valid_time_format # Добавлен is_valid_time_format
from typing import Dict, Any, List, Optional


class MainApplication:
    """
    Главный класс приложения GUI, использующий MVVM.
    Оркестрирует вкладки и взаимодействие с ViewModel.
    """

    def __init__(self, root: tk.Tk, view_model: VideoViewModel):
        """Инициализация главного окна."""
        self.root = root
        self.vm = view_model
        self.vm.add_listener(self._handle_vm_notification)

        self.root.title("Обработчик видео и медиа") # Обновлено название
        self.root.geometry("850x750") # Немного увеличим размер окна

        # --- Стиль ---
        style = ttk.Style()
        try:
            # Попробуем темы в порядке предпочтения
            available_themes = style.theme_names()
            if 'clam' in available_themes:
                style.theme_use('clam')
            elif 'vista' in available_themes: # Для Windows
                style.theme_use('vista')
            elif 'aqua' in available_themes: # Для macOS
                 style.theme_use('aqua')
            # Иначе останется тема по умолчанию
        except tk.TclError:
            print("Предупреждение: Не удалось применить предпочтительную тему, используется тема по умолчанию.")

        # --- Основная структура: Notebook для вкладок ---
        main_notebook = ttk.Notebook(self.root)
        main_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Создание вкладок ---
        process_tab_frame = ttk.Frame(main_notebook)
        trim_tab_frame = ttk.Frame(main_notebook) # Добавлен фрейм для обрезки
        settings_tab_frame = ttk.Frame(main_notebook)

        main_notebook.add(process_tab_frame, text='Обработка URL') # Уточнено название
        main_notebook.add(trim_tab_frame, text='Обрезка файла') # Добавлена вкладка
        main_notebook.add(settings_tab_frame, text='Настройки')

        # Создаем экземпляры классов вкладок
        self.process_tab = ProcessTab(process_tab_frame)
        self.process_tab.pack(fill=tk.BOTH, expand=True)

        self.trim_tab = TrimTab(trim_tab_frame) # Создан экземпляр TrimTab
        self.trim_tab.pack(fill=tk.BOTH, expand=True)

        self.settings_tab = SettingsTab(settings_tab_frame)
        self.settings_tab.pack(fill=tk.BOTH, expand=True)

        # --- Привязка команд к кнопкам ---
        self.process_tab.start_btn.configure(command=self._on_start_url_processing) # Переименовано для ясности
        self.process_tab.clear_log_btn.configure(command=self._clear_log)
        self.trim_tab.trim_btn.configure(command=self._on_start_trim) # Привязка кнопки обрезки

        # --- Состояние ---
        self._is_running_url_processing = False # Отдельный флаг для URL
        self._is_running_trim = False           # Отдельный флаг для обрезки

        # --- Начальные проверки ---
        self._check_external_tools()

        # Запуск периодической проверки очереди ViewModel
        self.root.after(constants.QUEUE_POLL_INTERVAL_MS, self._check_vm_queue_periodically)

    def _check_external_tools(self):
        """Проверяет наличие yt-dlp и ffmpeg при запуске."""
        missing = []
        ytdlp_path_const = constants.YTDLP_PATH
        ffmpeg_path_const = constants.FFMPEG_PATH

        # Проверяем yt-dlp (нужен для вкладки Обработка URL)
        try:
            if not find_executable('yt-dlp', ytdlp_path_const): missing.append('yt-dlp (требуется для обработки URL)')
        except Exception as e:
            print(f"Ошибка проверки yt-dlp: {e}")
            missing.append('yt-dlp (ошибка проверки)')

        # Проверяем ffmpeg (нужен для слияния аудио И для обрезки)
        try:
            if not find_executable('ffmpeg', ffmpeg_path_const): missing.append('ffmpeg (требуется для слияния аудио и обрезки)')
        except Exception as e:
            print(f"Ошибка проверки ffmpeg: {e}")
            missing.append('ffmpeg (ошибка проверки)')

        if missing:
            messagebox.showwarning(
                 "Отсутствуют внешние утилиты",
                 f"Не удалось найти следующие требуемые утилиты:\n\n"
                 f"- {', '.join(missing)}\n\n"
                 f"Убедитесь, что они установлены и доступны через системную переменную PATH, "
                 f"или укажите полные пути к ним в файле 'constants.py'.\n\n"
                 f"Соответствующие функции могут завершиться ошибкой."
             )
            self._add_log_message(f"[WARN] Отсутствуют требуемые утилиты: {', '.join(missing)}. Проверьте установку/PATH/constants.py.", "WARN")
        else:
             self._add_log_message("[INFO] Внешние утилиты (yt-dlp, ffmpeg) найдены.", "INFO")


    def _set_controls_state(self, enabled: bool):
        """Включает или отключает элементы управления на всех вкладках."""
        # Блокируем/разблокируем элементы в зависимости от того, какой процесс запущен
        # Если НЕ запущена обработка URL И НЕ запущена обрезка, то все можно включить
        can_enable_all = not self._is_running_url_processing and not self._is_running_trim

        # Вкладка обработки URL блокируется, если запущена обработка URL ИЛИ обрезка
        self.process_tab.set_enabled(not self._is_running_url_processing and not self._is_running_trim)

        # Вкладка обрезки блокируется, если запущена обрезка ИЛИ обработка URL
        self.trim_tab.set_enabled(not self._is_running_trim and not self._is_running_url_processing)

        # Вкладка настроек блокируется, если запущена обработка URL (обрезка ее не использует)
        self.settings_tab.set_enabled(not self._is_running_url_processing)

        # Кнопку "Очистить лог" можно оставить активной всегда
        try:
             if self.process_tab.clear_log_btn.winfo_exists():
                 self.process_tab.clear_log_btn.configure(state=tk.NORMAL)
        except tk.TclError:
            pass

    def _add_log_message(self, message: str, level: str = "INFO"):
        """Добавляет сообщение в область лога на вкладке ProcessTab."""
        # Лог теперь общий, добавляем туда все сообщения
        self.process_tab.add_log_message(message, level)

    def _clear_log(self):
        """Очищает область лога на вкладке ProcessTab."""
        self.process_tab.clear_log()

    def _validate_settings(self, settings: Dict[str, Any]) -> List[str]:
        """Выполняет базовую проверку словаря настроек (с вкладки Настройки)."""
        errors = []
        try:
            vol_orig = float(settings['original_volume'])
            if vol_orig < 0: errors.append("Громкость оригинала не может быть отрицательной.")
        except ValueError:
            errors.append("Громкость оригинала должна быть числом (например, 0.0, 0.5, 1.0).")
        try:
            vol_added = float(settings['added_volume'])
            if vol_added < 0: errors.append("Громкость добавленного аудио не может быть отрицательной.")
        except ValueError:
            errors.append("Громкость добавленного аудио должна быть числом (например, 1.0, 1.5).")

        # Простая проверка кода языка (2-3 буквы, опционально дефис и еще буквы/цифры)
        lang_pattern = re.compile(r"^[a-z]{2,3}(?:-[a-zA-Z0-9]{2,8})?$", re.IGNORECASE)
        if not settings['source_lang'] or not lang_pattern.match(settings['source_lang']):
             errors.append("Исходный язык должен быть кодом (например, en, ru, pt-br).")
        if not settings['target_lang'] or not lang_pattern.match(settings['target_lang']):
             errors.append("Целевой язык должен быть кодом (например, en, ru, pt-br).")
        if not settings['subtitle_lang'] or not lang_pattern.match(settings['subtitle_lang']):
             errors.append("Язык скачивания субтитров должен быть кодом (например, en, ru, pt-br).")


        if not settings['subtitle_format'].strip(): errors.append("Формат субтитров не может быть пустым.")
        if not settings['yt_dlp_format'].strip(): errors.append("Код формата видео (yt-dlp) не может быть пустым.")
        if not settings['video_format_ext'].strip(): errors.append("Контейнер видео на выходе не может быть пустым.")
        if not settings['merged_audio_codec'].strip(): errors.append("Аудио кодек после слияния не может быть пустым.")

        return errors

    def _on_start_url_processing(self):
        """Обрабатывает нажатие кнопки 'Начать обработку URL'."""
        if self._is_running_url_processing:
            self._add_log_message("[WARN] Обработка URL уже запущена.", "WARN")
            return
        if self._is_running_trim:
             self._add_log_message("[WARN] Дождитесь завершения обрезки файла.", "WARN")
             return

        # --- 1. Сбор данных ---
        url = self.process_tab.get_url()
        yandex_audio_path = self.process_tab.get_yandex_audio()
        output_dir = self.process_tab.get_output_dir()
        selected_actions = self.process_tab.get_selected_actions()
        settings = self.settings_tab.get_settings()

        # --- 2. Валидация ---
        errors = []
        # Простая проверка URL (должен начинаться с http/https)
        if not url or not (url.startswith("http://") or url.startswith("https://")):
             errors.append("- URL видео должен быть указан и начинаться с http:// или https://.")
        if not selected_actions: errors.append("- Должно быть выбрано хотя бы одно действие.")
        if not output_dir:
            errors.append("- Папка вывода обязательна.")
        else:
            # Попытка создать папку, если она не существует
            try:
                if not os.path.isdir(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                    self._add_log_message(f"[INFO] Создана папка вывода: {output_dir}", "INFO")
            except OSError as e:
                errors.append(f"- Не удалось создать папку вывода '{output_dir}': {e}")

        # Проверка аудиофайла, если выбрано действие 'da'
        if 'da' in selected_actions:
            if not yandex_audio_path:
                errors.append("- Внешний аудио файл обязателен для действия 'Смешать аудио'.")
            elif not os.path.exists(yandex_audio_path):
                 errors.append(f"- Внешний аудио файл не найден: {yandex_audio_path}")

        # Валидация настроек
        setting_errors = self._validate_settings(settings)
        if setting_errors:
            errors.append("\nПожалуйста, проверьте вкладку Настройки:")
            errors.extend([f"- {err}" for err in setting_errors])

        if errors:
            error_message = "Пожалуйста, исправьте следующие ошибки:\n\n" + "\n".join(errors)
            messagebox.showerror("Ошибка ввода (Обработка URL)", error_message)
            return

        # --- 3. Запуск обработки ---
        self._is_running_url_processing = True
        self._set_controls_state(enabled=False) # Блокируем ВСЕ элементы управления
        self.process_tab.start_progress()
        self._add_log_message("=" * 60, "INFO")
        self._add_log_message(">>> Запуск обработки URL...", "INFO")
        self._add_log_message(f"[INFO] URL: {url}", "INFO")
        self._add_log_message(f"[INFO] Действия: {selected_actions}", "INFO")
        self._add_log_message(f"[INFO] Папка вывода: {output_dir}", "INFO")
        # Доп. логи настроек (опционально)
        # self._add_log_message(f"[DEBUG] Настройки: {settings}", "DEBUG")

        try:
            self.vm.run(url, yandex_audio_path, selected_actions, output_dir, settings)
        except Exception as e:
            self._add_log_message(f"[ERROR] Не удалось запустить поток обработки URL: {e}", "ERROR")
            self._add_log_message(f"[DEBUG] Traceback:\n{traceback.format_exc()}", "DEBUG")
            messagebox.showerror("Критическая ошибка", f"Не удалось начать обработку URL: {e}")
            self.process_tab.stop_progress()
            self._is_running_url_processing = False
            self._set_controls_state(enabled=True) # Разблокируем элементы управления

    def _on_start_trim(self):
        """Обрабатывает нажатие кнопки 'Начать обрезку'."""
        if self._is_running_trim:
            self._add_log_message("[WARN][TRIM] Обрезка уже запущена.", "WARN")
            return
        if self._is_running_url_processing:
            self._add_log_message("[WARN][TRIM] Дождитесь завершения обработки URL.", "WARN")
            return

        # --- 1. Сбор данных ---
        input_path = self.trim_tab.get_input_path()
        output_path = self.trim_tab.get_output_path()
        start_time = self.trim_tab.get_start_time()
        end_time = self.trim_tab.get_end_time()

        # --- 2. Валидация ---
        errors = []
        if not input_path:
            errors.append("- Входной файл обязателен.")
        elif not os.path.isfile(input_path):
            errors.append(f"- Входной файл не найден или не является файлом: {input_path}")

        if not output_path:
             errors.append("- Выходной файл обязателен.")
        else:
             # Проверка возможности записи в директорию выходного файла
             output_dir = os.path.dirname(output_path)
             if not output_dir: # Если указано только имя файла, используем текущую директорию
                 output_dir = "."
             if not os.path.isdir(output_dir):
                 try:
                     os.makedirs(output_dir, exist_ok=True)
                     self._add_log_message(f"[INFO][TRIM] Создана выходная директория: {output_dir}", "INFO")
                 except OSError as e:
                     errors.append(f"- Не удалось создать выходную директорию '{output_dir}': {e}")
             elif not os.access(output_dir, os.W_OK):
                 errors.append(f"- Нет прав на запись в выходную директорию: {output_dir}")

        if not is_valid_time_format(start_time):
            errors.append("- Неверный формат времени начала (ожидается ЧЧ:ММ:СС или ЧЧ:ММ:СС.мс).")
        if not is_valid_time_format(end_time):
            errors.append("- Неверный формат времени окончания (ожидается ЧЧ:ММ:СС или ЧЧ:ММ:СС.мс).")

        # Дополнительно можно сравнить время начала и конца, но ffmpeg обработает это
        # (если end < start, результат будет нулевой длины)

        if errors:
            error_message = "Пожалуйста, исправьте следующие ошибки:\n\n" + "\n".join(errors)
            messagebox.showerror("Ошибка ввода (Обрезка)", error_message)
            return

        # --- 3. Запуск обрезки ---
        self._is_running_trim = True
        self._set_controls_state(enabled=False) # Блокируем ВСЕ элементы управления
        self.process_tab.start_progress() # Используем общий прогресс-бар
        self._add_log_message("=" * 60, "TRIM")
        self._add_log_message(">>> Запуск обрезки файла...", "TRIM")
        self._add_log_message(f"[TRIM] Вход: {input_path}", "TRIM")
        self._add_log_message(f"[TRIM] Выход: {output_path}", "TRIM")
        self._add_log_message(f"[TRIM] Старт: {start_time}, Конец: {end_time}", "TRIM")

        try:
            self.vm.run_trim(input_path, output_path, start_time, end_time)
        except Exception as e:
            self._add_log_message(f"[ERROR][TRIM] Не удалось запустить поток обрезки: {e}", "ERROR")
            self._add_log_message(f"[DEBUG] Traceback:\n{traceback.format_exc()}", "DEBUG")
            messagebox.showerror("Критическая ошибка", f"Не удалось начать обрезку: {e}")
            self.process_tab.stop_progress()
            self._is_running_trim = False
            self._set_controls_state(enabled=True) # Разблокируем элементы управления

    # --- Обработка уведомлений от ViewModel ---
    def _handle_vm_notification(self, message: Dict[str, Any]):
        """Обрабатывает уведомления от ViewModel (просто планирует проверку очереди)."""
        if hasattr(self, 'root') and self.root.winfo_exists():
            # Запланировать вызов _process_vm_queue в основном потоке GUI
            self.root.after(0, self._process_vm_queue)

    def _process_vm_queue(self):
        """Обрабатывает сообщения из очереди ViewModel в основном потоке GUI."""
        if not hasattr(self, 'root') or not self.root.winfo_exists():
             return # Окно закрыто

        try:
            while True: # Обрабатываем все сообщения в очереди за раз
                message = self.vm.get_message_from_queue()
                if message is None:
                    break # Очередь пуста

                msg_type = message.get("type")
                msg_data = message.get("data")
                msg_level = message.get("level", "INFO")
                msg_origin = message.get("origin", "url") # Добавляем источник сообщения (url/trim)

                if msg_type == "log":
                    self._add_log_message(str(msg_data), msg_level)
                elif msg_type == "status":
                    is_success = (msg_data == "finished")
                    log_level = "SUCCESS" if is_success else "ERROR"

                    if msg_origin == "url":
                        # Завершилась обработка URL
                        if msg_data == "running":
                           pass # Состояние уже установлено
                        elif msg_data == "finished" or msg_data == "error":
                            self.process_tab.stop_progress()
                            self._is_running_url_processing = False
                            self._set_controls_state(enabled=True) # Разблокируем контролы

                            result_message = "✅ Обработка URL успешно завершена." if is_success else "❌ Обработка URL завершена с ошибками."
                            self._add_log_message(f">>> {result_message}", log_level)
                            self._add_log_message("=" * 60, "INFO")

                            if is_success:
                                messagebox.showinfo("Обработка URL завершена", "Выбранные задачи успешно выполнены.")
                            else:
                                messagebox.showerror("Ошибка обработки URL", "Во время обработки URL произошла ошибка. Проверьте лог.")
                    elif msg_origin == "trim":
                        # Завершилась обрезка
                         if msg_data == "running":
                            pass # Состояние уже установлено
                         elif msg_data == "finished" or msg_data == "error":
                            self.process_tab.stop_progress() # Используем общий прогресс-бар
                            self._is_running_trim = False
                            self._set_controls_state(enabled=True) # Разблокируем контролы

                            result_message = "✅ Обрезка файла успешно завершена." if is_success else "❌ Обрезка файла завершена с ошибками."
                            self._add_log_message(f">>> {result_message}", log_level)
                            self._add_log_message("=" * 60, "TRIM") # Используем тег TRIM

                            if is_success:
                                messagebox.showinfo("Обрезка завершена", f"Файл успешно обрезан:\n{self.trim_tab.get_output_path()}")
                            else:
                                messagebox.showerror("Ошибка обрезки", "Во время обрезки файла произошла ошибка. Проверьте лог.")

        except Exception as e:
            print(f"КРИТИЧЕСКАЯ ОШИБКА обработки очереди ViewModel: {e}", flush=True)
            traceback.print_exc()
            # Попытка записать ошибку в лог GUI, если это возможно
            try:
                 self._add_log_message(f"[ERROR] Внутренняя ошибка GUI при обработке очереди: {e}", "ERROR")
            except: pass

    def _check_vm_queue_periodically(self):
        """Периодически проверяет очередь ViewModel."""
        if not hasattr(self, 'root') or not self.root.winfo_exists():
             return # Окно было закрыто
        self._process_vm_queue()
        # Перепланируем следующую проверку
        self.root.after(constants.QUEUE_POLL_INTERVAL_MS, self._check_vm_queue_periodically)


# --- Функция запуска GUI ---
def create_gui():
    """Создает корневое окно Tkinter, ViewModel, GUI и запускает главный цикл."""
    root = tk.Tk()
    vm = VideoViewModel()
    app = MainApplication(root, vm)
    root.mainloop()