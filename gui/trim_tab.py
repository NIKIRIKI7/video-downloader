import tkinter as tk
from tkinter import ttk, filedialog
import os
from typing import List, Optional

import constants
from utils.utils import is_valid_time_format, generate_trimmed_filename

class TrimTab(ttk.Frame):
    """Класс для вкладки обрезки медиафайлов."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.input_widgets: List[tk.Widget] = [] # Для управления состоянием
        self._create_widgets()

    def _create_widgets(self):
        """Создает виджеты на вкладке обрезки."""
        trim_frame = ttk.Frame(self, padding=15)
        trim_frame.pack(fill=tk.BOTH, expand=True)
        trim_frame.columnconfigure(1, weight=1) # Растягивать поля ввода

        current_row = 0

        # --- Выбор файла ---
        file_frame = ttk.LabelFrame(trim_frame, text="Файлы", padding=10)
        file_frame.grid(row=current_row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        file_frame.columnconfigure(1, weight=1) # Растягивать поле ввода
        current_row += 1

        ttk.Label(file_frame, text="Входной файл (видео/аудио):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.input_path_ent = ttk.Entry(file_frame, width=60)
        self.input_path_ent.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3)
        self.browse_input_btn = ttk.Button(file_frame, text="Обзор...", command=self._browse_input_file)
        self.browse_input_btn.grid(row=0, column=2, padx=(5, 0), pady=3)
        self.input_widgets.extend([self.input_path_ent, self.browse_input_btn])

        ttk.Label(file_frame, text="Выходной файл:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.output_path_ent = ttk.Entry(file_frame, width=60)
        self.output_path_ent.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=3)
        self.browse_output_btn = ttk.Button(file_frame, text="Обзор...", command=self._browse_output_file)
        self.browse_output_btn.grid(row=1, column=2, padx=(5, 0), pady=3)
        # Кнопка "Сгенерировать имя"
        self.generate_name_btn = ttk.Button(file_frame, text="Сгенерировать", command=self._generate_output_name)
        self.generate_name_btn.grid(row=1, column=3, padx=(5, 0), pady=3)
        self.input_widgets.extend([self.output_path_ent, self.browse_output_btn, self.generate_name_btn])


        # --- Параметры обрезки ---
        time_frame = ttk.LabelFrame(trim_frame, text="Параметры обрезки", padding=10)
        time_frame.grid(row=current_row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        time_frame.columnconfigure(1, weight=0) # Не растягивать поля времени
        time_frame.columnconfigure(3, weight=0)
        current_row += 1

        ttk.Label(time_frame, text="Время начала (ЧЧ:ММ:СС.мс):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.start_time_var = tk.StringVar(value="00:00:00.000")
        self.start_time_ent = ttk.Entry(time_frame, textvariable=self.start_time_var, width=15)
        self.start_time_ent.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(time_frame, text="Время окончания (ЧЧ:ММ:СС.мс):").grid(row=0, column=2, sticky=tk.W, padx=(20, 5), pady=3)
        self.end_time_var = tk.StringVar(value="00:00:10.000")
        self.end_time_ent = ttk.Entry(time_frame, textvariable=self.end_time_var, width=15)
        self.end_time_ent.grid(row=0, column=3, sticky=tk.W, padx=5, pady=3)
        self.input_widgets.extend([self.start_time_ent, self.end_time_ent])

        # --- Кнопка запуска ---
        # Кнопка будет привязана к методу в MainApplication
        self.trim_btn = ttk.Button(trim_frame, text="Начать обрезку")
        # Размещаем кнопку ниже с отступом
        self.trim_btn.grid(row=current_row, column=0, columnspan=3, pady=(15, 5))
        self.input_widgets.append(self.trim_btn)

    def _browse_input_file(self):
        """Открывает диалог выбора входного медиафайла."""
        filename = filedialog.askopenfilename(
            title="Выберите видео или аудио файл для обрезки",
            filetypes=[("Медиа файлы", "*.mp4 *.mkv *.avi *.mov *.webm *.mp3 *.wav *.m4a *.aac *.ogg"), ("Все файлы", "*.*")]
        )
        if filename:
            self.input_path_ent.delete(0, tk.END)
            self.input_path_ent.insert(0, filename)
            # Попытка авто-генерации выходного имени при выборе входного
            self._generate_output_name()

    def _browse_output_file(self):
        """Открывает диалог сохранения выходного файла."""
        input_path = self.get_input_path()
        initial_dir = os.path.dirname(input_path) if input_path else constants.VIDEO_DIR_DEFAULT
        initial_file = os.path.basename(self.get_output_path()) # Используем текущее значение, если есть
        if not initial_file and input_path:
            # Если выходное поле пустое, генерируем имя на основе входного
            try:
                initial_file = generate_trimmed_filename(input_path, self.get_start_time(), self.get_end_time())
            except Exception: # Если время некорректно, используем базовое имя
                initial_file = os.path.basename(input_path)

        # Определяем тип файла по расширению входного файла
        default_extension = os.path.splitext(input_path)[1] if input_path else ".mp4"
        filetypes = [("Соответствующий тип", f"*{default_extension}"), ("Все файлы", "*.*")]
        # Добавляем стандартные типы
        known_video = [("Видео MP4", "*.mp4"), ("Видео MKV", "*.mkv")]
        known_audio = [("Аудио MP3", "*.mp3"), ("Аудио AAC", "*.aac"), ("Аудио WAV", "*.wav")]
        if default_extension.lower() in ['.mp4', '.mkv', '.avi', '.mov', '.webm']:
            filetypes.extend(known_video)
            filetypes.extend(known_audio)
        elif default_extension.lower() in ['.mp3', '.wav', '.m4a', '.aac', '.ogg']:
             filetypes.extend(known_audio)
             filetypes.extend(known_video)


        filename = filedialog.asksaveasfilename(
            title="Сохранить обрезанный файл как...",
            initialdir=initial_dir,
            initialfile=initial_file,
            defaultextension=default_extension,
            filetypes=filetypes
        )
        if filename:
            self.output_path_ent.delete(0, tk.END)
            self.output_path_ent.insert(0, filename)

    def _generate_output_name(self):
        """Генерирует предлагаемое имя выходного файла на основе входного и времени."""
        input_path = self.get_input_path()
        start_time = self.get_start_time()
        end_time = self.get_end_time()

        # Простая валидация перед генерацией
        if not input_path or not os.path.exists(input_path):
            # Не генерируем имя без валидного входного файла
             # Можно показать сообщение, но пока просто ничего не делаем
            return
        if not is_valid_time_format(start_time) or not is_valid_time_format(end_time):
             # Не генерируем имя без валидного времени
             return

        try:
            generated_name = generate_trimmed_filename(input_path, start_time, end_time)
            output_dir = os.path.dirname(input_path) # Предлагаем сохранить в той же папке
            full_output_path = os.path.join(output_dir, os.path.basename(generated_name))

            self.output_path_ent.delete(0, tk.END)
            self.output_path_ent.insert(0, full_output_path)
        except Exception as e:
            print(f"Ошибка генерации имени файла: {e}") # Лог в консоль для отладки

    # --- Методы для доступа к данным и управления ---
    def get_input_path(self) -> str:
        """Возвращает путь к входному файлу."""
        return self.input_path_ent.get().strip()

    def get_output_path(self) -> str:
        """Возвращает путь к выходному файлу."""
        return self.output_path_ent.get().strip()

    def get_start_time(self) -> str:
        """Возвращает время начала обрезки."""
        return self.start_time_var.get().strip()

    def get_end_time(self) -> str:
        """Возвращает время окончания обрезки."""
        return self.end_time_var.get().strip()

    def set_enabled(self, enabled: bool):
        """Включает или отключает поля ввода и кнопки на вкладке."""
        widget_state = tk.NORMAL if enabled else tk.DISABLED
        for widget in self.input_widgets:
             if widget is not None and widget.winfo_exists():
                try:
                    if isinstance(widget, (ttk.Entry, ttk.Button, tk.Entry)):
                         widget.configure(state=widget_state)
                except tk.TclError:
                    pass # Игнорировать ошибки