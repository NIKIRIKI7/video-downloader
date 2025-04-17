import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
import os
from typing import Dict, List, Optional

import constants # Для значений по умолчанию


class ProcessTab(ttk.Frame):
    """Класс для вкладки обработки видео."""

    # Определения действий вынесены сюда для удобства
    # Обновлено с добавлением 'tp'
    ACTION_DEFINITIONS = [
            ('tp', '0. Скачать превью видео'),
            ('md', '1. Скачать метаданные (ID, Заголовок, Описание)'),
            ('dv', '2. Скачать видео'),
            ('ds', '3. Скачать субтитры'),
            ('dt', '4. Перевести субтитры'),
            ('da', '5. Смешать аудио (с файлом Yandex)'),
            ('tm', '6. Перевести метаданные'),
        ]

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.action_vars: Dict[str, tk.BooleanVar] = {}
        self.action_cbs: Dict[str, ttk.Checkbutton] = {}
        self.input_widgets: List[tk.Widget] = [] # Для управления состоянием
        self._create_widgets()

    def _create_widgets(self):
        """Создает виджеты на вкладке обработки."""
        # --- Поля ввода ---
        input_frame = ttk.LabelFrame(self, text="Входные данные", padding=10)
        input_frame.pack(fill=tk.X, pady=(5, 10), padx=5) # Добавлен padx
        input_frame.columnconfigure(1, weight=1)

        ttk.Label(input_frame, text="URL видео:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.url_ent = ttk.Entry(input_frame, width=60)
        self.url_ent.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3)
        self.input_widgets.append(self.url_ent)

        ttk.Label(input_frame, text="Аудио файл (Yandex):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.y_ent = ttk.Entry(input_frame, width=50)
        self.y_ent.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=3)
        self.browse_y_btn = ttk.Button(input_frame, text="Обзор...", command=self._browse_yandex_audio)
        self.browse_y_btn.grid(row=1, column=2, padx=(5, 0), pady=3)
        self.input_widgets.extend([self.y_ent, self.browse_y_btn])

        ttk.Label(input_frame, text="Папка вывода:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.out_dir_var = tk.StringVar(value=constants.VIDEO_DIR_DEFAULT)
        self.out_dir_ent = ttk.Entry(input_frame, textvariable=self.out_dir_var, width=50)
        self.out_dir_ent.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=3)
        self.browse_out_btn = ttk.Button(input_frame, text="Обзор...", command=self._browse_output_dir)
        self.browse_out_btn.grid(row=2, column=2, padx=(5, 0), pady=3)
        self.input_widgets.extend([self.out_dir_ent, self.browse_out_btn])

        # --- Действия ---
        actions_frame = ttk.LabelFrame(self, text="Действия (для URL)", padding=10)
        actions_frame.pack(fill=tk.X, pady=5, padx=5) # Добавлен padx
        cols = 2 # Количество колонок для чекбоксов
        for i, (key, label) in enumerate(self.ACTION_DEFINITIONS):
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(actions_frame, text=label, variable=var)
            row, col = divmod(i, cols)
            cb.grid(row=row, column=col, padx=10, pady=3, sticky=tk.W)
            self.action_vars[key] = var
            self.action_cbs[key] = cb
        # Настройка растяжения колонок в actions_frame
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)
        self.input_widgets.extend(self.action_cbs.values())


        # --- Лог ---
        log_frame = ttk.LabelFrame(self, text="Лог выполнения", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5, padx=5) # Добавлен padx
        self.log_txt = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9) if os.name == 'nt' else ("Monaco", 10) if os.name == 'posix' else ("Courier", 10))
        self.log_txt.pack(fill=tk.BOTH, expand=True)
        self.log_txt.tag_configure("INFO", foreground="black")
        self.log_txt.tag_configure("WARN", foreground="#E69900") # Оранжевый
        self.log_txt.tag_configure("ERROR", foreground="red")
        self.log_txt.tag_configure("DEBUG", foreground="grey")
        self.log_txt.tag_configure("SUCCESS", foreground="green")
        self.log_txt.tag_configure("TRIM", foreground="blue") # Цвет для логов обрезки

        # --- Прогресс и Управление ---
        progress_control_frame = ttk.Frame(self)
        progress_control_frame.pack(fill=tk.X, pady=(5, 5), padx=5) # Добавлен padx и отступ снизу
        progress_control_frame.columnconfigure(0, weight=1) # Центральная колонка с кнопками
        progress_control_frame.columnconfigure(1, weight=1) # Правая часть для растяжения

        self.progress = ttk.Progressbar(progress_control_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.EW)

        # Кнопка Start будет привязана к методу в MainApplication
        self.start_btn = ttk.Button(progress_control_frame, text="Начать обработку URL")
        self.start_btn.grid(row=1, column=0, padx=5, pady=(10, 0), sticky=tk.E) # Выравнивание вправо

        # Кнопка Clear Log будет привязана к методу в MainApplication
        self.clear_log_btn = ttk.Button(progress_control_frame, text="Очистить лог")
        self.clear_log_btn.grid(row=1, column=1, padx=5, pady=(10, 0), sticky=tk.W) # Выравнивание влево


        self.input_widgets.append(self.start_btn) # Кнопку Start тоже блокируем
        # Кнопку Clear Log не добавляем в input_widgets, чтобы она всегда была активна

    def _browse_yandex_audio(self):
        """Открывает диалог выбора аудио файла."""
        filename = filedialog.askopenfilename(
            title="Выберите внешний аудио файл",
            filetypes=[("Аудио файлы", "*.mp3 *.m4a *.aac *.wav *.ogg"), ("Все файлы", "*.*")]
        )
        if filename:
            self.y_ent.delete(0, tk.END)
            self.y_ent.insert(0, filename)

    def _browse_output_dir(self):
        """Открывает диалог выбора папки вывода."""
        initial_dir = self.out_dir_var.get()
        if not os.path.isdir(initial_dir):
            initial_dir = constants.VIDEO_DIR_DEFAULT
        dirname = filedialog.askdirectory(
            title="Выберите папку вывода",
            initialdir=initial_dir,
            mustexist=False # Позволяем создать папку, если её нет
        )
        if dirname:
            self.out_dir_var.set(dirname)

    # --- Методы для доступа к данным и управления ---
    def get_url(self) -> str:
        """Возвращает введенный URL."""
        return self.url_ent.get().strip()

    def get_yandex_audio(self) -> str:
        """Возвращает путь к файлу Yandex Audio."""
        return self.y_ent.get().strip()

    def get_output_dir(self) -> str:
        """Возвращает путь к папке вывода."""
        return self.out_dir_var.get().strip()

    def get_selected_actions(self) -> List[str]:
        """Возвращает список ключей выбранных действий."""
        return [key for key, var in self.action_vars.items() if var.get()]

    def add_log_message(self, message: str, level: str = "INFO"):
        """Добавляет сообщение в лог с указанным уровнем (тегом)."""
        if not hasattr(self, 'log_txt') or not self.log_txt.winfo_exists():
            print(f"LOG ({level}): {message}") # Резервный вывод в консоль
            return
        try:
            self.log_txt.config(state=tk.NORMAL)
            # Определяем тег по уровню, добавляем 'TRIM'
            tag = level.upper()
            if tag not in ["INFO", "WARN", "ERROR", "DEBUG", "SUCCESS", "TRIM"]:
                tag = "INFO" # По умолчанию INFO
            self.log_txt.insert(tk.END, message + "\n", tag)
            self.log_txt.see(tk.END) # Прокрутка к последнему сообщению
            self.log_txt.config(state=tk.DISABLED)
        except Exception as e:
            print(f"CRITICAL: Ошибка добавления сообщения в лог GUI: {e}", flush=True)
            print(f"Исходное сообщение ({level}): {message}", flush=True)

    def clear_log(self):
        """Очищает область лога."""
        if not hasattr(self, 'log_txt') or not self.log_txt.winfo_exists():
            return
        try:
            self.log_txt.config(state=tk.NORMAL)
            self.log_txt.delete('1.0', tk.END)
            self.log_txt.config(state=tk.DISABLED)
        except Exception as e:
             print(f"Ошибка очистки лога GUI: {e}")

    def start_progress(self):
        """Запускает индикатор прогресса."""
        if hasattr(self, 'progress') and self.progress.winfo_exists():
            self.progress.start(10) # Число - интервал обновления в мс

    def stop_progress(self):
        """Останавливает индикатор прогресса."""
        if hasattr(self, 'progress') and self.progress.winfo_exists():
            self.progress.stop()

    def set_enabled(self, enabled: bool):
        """Включает или отключает поля ввода и кнопки на вкладке."""
        widget_state = tk.NORMAL if enabled else tk.DISABLED
        for widget in self.input_widgets:
             # Проверяем существование виджета перед изменением состояния
             if widget is not None and widget.winfo_exists():
                try:
                    # Checkbutton, Button, Entry используют configure
                    if isinstance(widget, (ttk.Entry, ttk.Button, ttk.Checkbutton, tk.Entry)):
                        widget.configure(state=widget_state)
                except tk.TclError:
                    pass # Игнорировать ошибки для виджетов, которые могли быть уничтожены