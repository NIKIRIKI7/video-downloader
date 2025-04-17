# File: gui/main_window.py
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import queue
import os
import re # Для валидации
import traceback

# Используем относительные импорты внутри пакета gui
from .process_tab import ProcessTab
from .settings_tab import SettingsTab

# Импортируем ViewModel и другие зависимости
from viewmodel.video_viewmodel import VideoViewModel
import constants
from utils.utils import find_executable
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

        self.root.title("Обработчик видео")
        self.root.geometry("800x700")

        # --- Стиль ---
        style = ttk.Style()
        try:
            style.theme_use('clam')
        except tk.TclError:
            print("Warning: 'clam' theme not found, using default theme.")

        # --- Основная структура: Notebook для вкладок ---
        main_notebook = ttk.Notebook(self.root)
        main_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Создание вкладок ---
        # Создаем фреймы для каждой вкладки
        process_tab_frame = ttk.Frame(main_notebook)
        settings_tab_frame = ttk.Frame(main_notebook)

        # Добавляем фреймы в Notebook
        main_notebook.add(process_tab_frame, text='Обработка видео')
        main_notebook.add(settings_tab_frame, text='Настройки')

        # Создаем экземпляры классов вкладок, передавая родительский фрейм
        self.process_tab = ProcessTab(process_tab_frame)
        self.process_tab.pack(fill=tk.BOTH, expand=True)

        self.settings_tab = SettingsTab(settings_tab_frame)
        self.settings_tab.pack(fill=tk.BOTH, expand=True)

        # --- Привязка команд к кнопкам на вкладке ProcessTab ---
        self.process_tab.start_btn.configure(command=self._on_start)
        self.process_tab.clear_log_btn.configure(command=self._clear_log)

        # --- Состояние ---
        self._is_running = False

        # --- Начальные проверки ---
        self._check_external_tools()

        # Запуск периодической проверки очереди ViewModel
        self.root.after(constants.QUEUE_POLL_INTERVAL_MS, self._check_vm_queue_periodically)

    def _check_external_tools(self):
        """Проверяет наличие yt-dlp и ffmpeg при запуске."""
        missing = []
        ytdlp_path_const = constants.YTDLP_PATH
        ffmpeg_path_const = constants.FFMPEG_PATH

        try:
            if not find_executable('yt-dlp', ytdlp_path_const): missing.append('yt-dlp')
        except Exception as e:
            print(f"Error checking for yt-dlp: {e}")
            missing.append('yt-dlp (ошибка проверки)')

        try:
            if not find_executable('ffmpeg', ffmpeg_path_const): missing.append('ffmpeg')
        except Exception as e:
            print(f"Error checking for ffmpeg: {e}")
            missing.append('ffmpeg (ошибка проверки)')

        if missing:
            messagebox.showwarning(
                 "Отсутствуют внешние утилиты",
                 f"Не удалось найти следующие требуемые утилиты:\n\n"
                 f"- {', '.join(missing)}\n\n"
                 f"Убедитесь, что они установлены и доступны через системную переменную PATH, "
                 f"или укажите полные пути к ним в файле 'constants.py'.\n\n"
                 f"Действия, требующие эти утилиты, могут завершиться ошибкой."
             )
            self._add_log_message(f"[WARN] Отсутствуют требуемые утилиты: {', '.join(missing)}. Проверьте установку/PATH/constants.py.", "WARN")

    def _set_controls_state(self, enabled: bool):
        """Включает или отключает элементы управления на обеих вкладках."""
        self.process_tab.set_enabled(enabled)
        self.settings_tab.set_enabled(enabled)
        # Кнопку "Очистить лог" можно оставить активной всегда
        # self.process_tab.clear_log_btn.configure(state='normal' if enabled else 'disabled')


    def _add_log_message(self, message: str, level: str = "INFO"):
        """Добавляет сообщение в область лога на вкладке ProcessTab."""
        # Делегируем добавление лога экземпляру ProcessTab
        self.process_tab.add_log_message(message, level)

    def _clear_log(self):
        """Очищает область лога на вкладке ProcessTab."""
         # Делегируем очистку лога экземпляру ProcessTab
        self.process_tab.clear_log()

    def _validate_settings(self, settings: Dict[str, Any]) -> List[str]:
        """Выполняет базовую проверку словаря настроек (полученного от SettingsTab)."""
        # Эта логика остается в MainApplication, т.к. она общая
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

        lang_pattern = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z]{2,4})?$")
        if not settings['source_lang']: errors.append("Исходный язык не может быть пустым.")
        if not settings['target_lang']: errors.append("Целевой язык не может быть пустым.")
        if not settings['subtitle_lang']: errors.append("Язык скачивания субтитров не может быть пустым.")

        if not settings['subtitle_format'].strip(): errors.append("Формат субтитров не может быть пустым.")
        if not settings['yt_dlp_format'].strip(): errors.append("Код формата видео (yt-dlp) не может быть пустым.")
        if not settings['video_format_ext'].strip(): errors.append("Контейнер видео на выходе не может быть пустым.")
        if not settings['merged_audio_codec'].strip(): errors.append("Аудио кодек после слияния не может быть пустым.")

        return errors

    def _on_start(self):
        """Обрабатывает нажатие кнопки 'Начать обработку'."""
        if self._is_running:
            self._add_log_message("[WARN] Обработка уже запущена.", "WARN")
            return

        # --- 1. Сбор данных с вкладок ---
        url = self.process_tab.get_url()
        yandex_audio_path = self.process_tab.get_yandex_audio()
        output_dir = self.process_tab.get_output_dir()
        selected_actions = self.process_tab.get_selected_actions()
        settings = self.settings_tab.get_settings() # Получаем настройки от SettingsTab

        # --- 2. Валидация ---
        errors = []
        if not url: errors.append("- URL видео обязателен.")
        if not selected_actions: errors.append("- Должно быть выбрано хотя бы одно действие.")
        if not output_dir:
            errors.append("- Папка вывода обязательна.")
        else:
            try:
                if not os.path.isdir(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                    self._add_log_message(f"[INFO] Создана папка вывода: {output_dir}", "INFO")
            except OSError as e:
                errors.append(f"- Не удалось создать папку вывода: {e}")

        if 'da' in selected_actions:
            if not yandex_audio_path:
                errors.append("- Внешний аудио файл обязателен для действия 'Смешать аудио'.")
            elif not os.path.exists(yandex_audio_path):
                 errors.append(f"- Внешний аудио файл не найден: {yandex_audio_path}")

        # Валидация самих настроек
        setting_errors = self._validate_settings(settings) # Валидируем полученный словарь
        if setting_errors:
            errors.append("\nПожалуйста, проверьте вкладку Настройки:")
            errors.extend([f"- {err}" for err in setting_errors])

        if errors:
            error_message = "Пожалуйста, исправьте следующие ошибки:\n\n" + "\n".join(errors)
            messagebox.showerror("Ошибка ввода", error_message)
            return

        # --- 3. Запуск обработки ---
        self._is_running = True
        self._set_controls_state(enabled=False)
        self.process_tab.start_progress() # Управляем прогресс-баром через ProcessTab
        self._add_log_message("=" * 60, "INFO")
        self._add_log_message(">>> Запуск обработки с текущими настройками...", "INFO")
        self._add_log_message(f"[INFO] Действия: {selected_actions}", "INFO")
        self._add_log_message(f"[INFO] Папка вывода: {output_dir}", "INFO")
        self._add_log_message(f"[INFO] Громкость (Ориг/Добав): {settings['original_volume']}/{settings['added_volume']}", "INFO")
        self._add_log_message(f"[INFO] Языки (Скач/Исход/Целев): {settings['subtitle_lang']}/{settings['source_lang']}/{settings['target_lang']}", "INFO")

        try:
            # Передаем собранные данные в ViewModel
            self.vm.run(url, yandex_audio_path, selected_actions, output_dir, settings)
        except Exception as e:
            self._add_log_message(f"[ERROR] Не удалось запустить поток обработки: {e}", "ERROR")
            self._add_log_message(f"[DEBUG] Traceback:\n{traceback.format_exc()}", "DEBUG")
            messagebox.showerror("Ошибка", f"Не удалось начать обработку: {e}")
            self.process_tab.stop_progress()
            self._set_controls_state(enabled=True)
            self._is_running = False


    # --- Обработка уведомлений от ViewModel ---
    def _handle_vm_notification(self, message: Dict[str, Any]):
        """Обрабатывает уведомления от ViewModel."""
        if hasattr(self, 'root') and self.root.winfo_exists():
            self.root.after(0, self._process_vm_queue)

    def _process_vm_queue(self):
        """Обрабатывает сообщения из очереди ViewModel."""
        if not hasattr(self, 'root') or not self.root.winfo_exists():
             return

        try:
            while True:
                message = self.vm.get_message_from_queue()
                if message is None: break

                msg_type = message.get("type")
                msg_data = message.get("data")
                msg_level = message.get("level", "INFO")

                if msg_type == "log":
                    self._add_log_message(str(msg_data), msg_level) # Используем метод для логирования
                elif msg_type == "status":
                    if msg_data == "running":
                        pass # Состояние уже установлено в _on_start
                    elif msg_data == "finished" or msg_data == "error":
                        self.process_tab.stop_progress() # Останавливаем прогресс через ProcessTab
                        self._set_controls_state(enabled=True)
                        self._is_running = False

                        is_success = (msg_data == "finished")
                        result_message = "✅ Обработка успешно завершена." if is_success else "❌ Обработка завершена с ошибками."
                        log_level = "SUCCESS" if is_success else "ERROR"

                        self._add_log_message(f">>> {result_message}", log_level)
                        self._add_log_message("=" * 60, "INFO")

                        if is_success:
                            messagebox.showinfo("Обработка завершена", "Выбранные задачи успешно выполнены.")
                        else:
                            messagebox.showerror("Ошибка обработки", "Во время обработки произошла ошибка. Пожалуйста, проверьте лог выполнения для получения подробной информации.")

        except Exception as e:
            print(f"CRITICAL ERROR processing ViewModel queue: {e}", flush=True)
            traceback.print_exc()
            try:
                 self._add_log_message(f"[ERROR] Внутренняя ошибка GUI при обработке очереди: {e}", "ERROR")
            except: pass

    def _check_vm_queue_periodically(self):
        """Периодически проверяет очередь ViewModel."""
        if not hasattr(self, 'root') or not self.root.winfo_exists():
             return
        self._process_vm_queue()
        self.root.after(constants.QUEUE_POLL_INTERVAL_MS, self._check_vm_queue_periodically)


# --- Функция запуска GUI ---
def create_gui():
    """Создает корневое окно Tkinter, ViewModel, GUI и запускает главный цикл."""
    root = tk.Tk()
    vm = VideoViewModel()
    app = MainApplication(root, vm) # Создаем экземпляр MainApplication
    root.mainloop()