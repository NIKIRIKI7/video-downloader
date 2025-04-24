# File: gui/main_window.py

import tkinter as tk
from tkinter import ttk, messagebox, Menu, filedialog
import threading
import os
import traceback
from pathlib import Path
from typing import Any, Dict

from .process_tab import ProcessTab
from .settings_tab import SettingsTab
from .trim_tab import TrimTab
from viewmodel.video_viewmodel import VideoViewModel
import constants
from utils.utils import find_executable, is_valid_time_format

class MainApplication:
    """
    Главное окно приложения с улучшенным UI/UX:
    - Меню Файл/Помощь
    - Центрирование окна
    - Иконки в вкладках
    - Статус-бар
    """
    def __init__(self, root: tk.Tk, view_model: VideoViewModel):
        self.root = root
        self.vm = view_model
        self.vm.add_listener(self._handle_vm_notification)

        # --- Настройка окна ---
        self.root.title("ВидеоОбработчик v1.2")
        self._center_window(900, 800)
        self._create_menu()

        # --- Стилизация ---
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TNotebook.Tab', padding=(10,6), font=('Segoe UI', 10))
        style.configure('TButton', font=('Segoe UI', 10))
        style.configure('Status.TLabel', font=('Segoe UI', 9))

        # --- Блокнот вкладок ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.process_tab = ProcessTab(self.notebook)
        self.trim_tab = TrimTab(self.notebook)
        self.settings_tab = SettingsTab(self.notebook)

        self.notebook.add(self.process_tab, text='📥 Обработка')
        self.notebook.add(self.trim_tab,   text='✂️ Обрезка')
        self.notebook.add(self.settings_tab, text='⚙️ Настройки')

        # --- Статус-бар ---
        self.status_var = tk.StringVar(value='Готово')
        status = ttk.Label(self.root, textvariable=self.status_var,
                           style='Status.TLabel', relief=tk.SUNKEN, anchor=tk.W, padding=(5,2))
        status.pack(fill=tk.X, side=tk.BOTTOM)

        # --- Привязка кнопок ---
        self.process_tab.start_btn.config(command=self._on_start_url_processing)
        self.process_tab.clear_log_btn.config(command=self._clear_log)
        self.trim_tab.trim_btn.config(command=self._on_start_trim)

        # Проверка внешних утилит после загрузки UI
        self.root.after(100, self._check_external_tools)

    def _center_window(self, width: int, height: int) -> None:
        ws, hs = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        x = (ws//2) - (width//2)
        y = (hs//2) - (height//2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _create_menu(self) -> None:
        menubar = Menu(self.root)
        file_menu = Menu(menubar, tearoff=0)
        file_menu.add_command(label='Выход', command=self.root.quit)
        menubar.add_cascade(label='Файл', menu=file_menu)

        help_menu = Menu(menubar, tearoff=0)
        help_menu.add_command(label='О программе', command=self._show_about)
        help_menu.add_command(label='Документация', command=self._open_docs)
        menubar.add_cascade(label='Помощь', menu=help_menu)

        self.root.config(menu=menubar)

    def _show_about(self) -> None:
        messagebox.showinfo('О программе', 'ВидеоОбработчик v1.2\nРазработано mcniki')

    def _open_docs(self) -> None:
        messagebox.showinfo('Документация', 'Документация находится в папке docs в корне проекта.')

    def _check_external_tools(self) -> None:
        missing = []
        for tool, display in [('yt-dlp','yt-dlp'), ('ffmpeg','FFmpeg')]:
            if not find_executable(tool, getattr(constants, f"{tool.upper()}_PATH")): missing.append(display)
        if missing:
            self._set_status('⚠️ Не найдены: ' + ', '.join(missing))
        else:
            self._set_status('✔️ Все утилиты доступны')

    def _set_status(self, text: str) -> None:
        self.status_var.set(text)

    def _add_log_message(self, message: str, level: str = 'INFO') -> None:
        self.process_tab.add_log_message(message, level)
        self._set_status(f"{level}: {message}")

    def _clear_log(self) -> None:
        self.process_tab.clear_log()
        self._set_status('Лог очищен')

    def _on_start_url_processing(self) -> None:
        self._set_status('Запуск обработки URL...')
        self._add_log_message('>>> Запуск обработки URL', 'INFO')
        self._run_url_flow()

    def _run_url_flow(self) -> None:
        url = self.process_tab.get_url()
        ya = self.process_tab.get_yandex_audio()
        out_dir = self.process_tab.get_output_dir()
        actions = self.process_tab.get_selected_actions()
        settings = self.settings_tab.get_settings()

        errors = []
        if not url.startswith(('http://','https://')): errors.append('Неверный URL')
        if not actions: errors.append('Не выбрано действие')
        if not out_dir: errors.append('Не указана папка вывода')
        if errors:
            messagebox.showerror('Ошибка ввода', '\n'.join(errors))
            self._set_status('Ошибка ввода')
            return

        try:
            self.vm.run(url, ya, actions, out_dir, settings)
        except Exception as e:
            messagebox.showerror('Критическая ошибка', str(e))
            self._set_status('Ошибка сервиса')

    def _on_start_trim(self) -> None:
        self._set_status('Запуск обрезки...')
        self._add_log_message('>>> Запуск обрезки', 'TRIM')
        self._run_trim_flow()

    def _run_trim_flow(self) -> None:
        inp = self.trim_tab.get_input_path()
        outp = self.trim_tab.get_output_path()
        st = self.trim_tab.get_start_time()
        et = self.trim_tab.get_end_time()

        errors = []
        if not inp or not os.path.isfile(inp): errors.append('Неверный входной файл')
        if not outp: errors.append('Не указан выходной файл')
        if not is_valid_time_format(st) or not is_valid_time_format(et): errors.append('Неверный формат времени')
        if errors:
            messagebox.showerror('Ошибка ввода (Обрезка)', '\n'.join(errors))
            self._set_status('Ошибка ввода')
            return

        try:
            self.vm.run_trim(inp, outp, st, et)
        except Exception as e:
            messagebox.showerror('Критическая ошибка', str(e))
            self._set_status('Ошибка обрезки')

    def _handle_vm_notification(self, msg: Dict[str, Any]) -> None:
        # Всегда вызывается в основном потоке через after
        if not hasattr(self, 'root') or not self.root.winfo_exists(): return
        self.root.after(0, self._process_vm_queue)

    def _process_vm_queue(self) -> None:
        while True:
            try:
                msg = self.vm.get_message_from_queue()
            except Exception:
                break
            if not msg: break

            mtype = msg.get('type')
            level = msg.get('level', 'INFO')
            data = msg.get('data')
            origin = msg.get('origin','url')

            if mtype == 'log':
                self._add_log_message(str(data), level)
            elif mtype == 'status':
                status = 'Успех' if data=='finished' else 'Ошибка'
                self._set_status(f"{origin}: {status}")

def create_gui():
    """Создает корневое окно Tkinter, ViewModel, GUI и запускает главный цикл."""
    root = tk.Tk()
    vm = VideoViewModel()
    app = MainApplication(root, vm)
    root.mainloop()