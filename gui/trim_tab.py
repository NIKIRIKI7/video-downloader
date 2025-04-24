# File: gui/trim_tab.py

import tkinter as tk
from tkinter import ttk, filedialog
from utils.utils import is_valid_time_format, generate_trimmed_filename

# Простой класс тултипов (можно импортировать из process_tab)
class ToolTip:
    def __init__(self, widget, text: str):
        self.widget = widget
        self.text = text
        self.tipwindow = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, event=None):
        if self.tipwindow or not self.text:
            return
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 20
        y += self.widget.winfo_rooty() + 20
        tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(tw, text=self.text, justify=tk.LEFT,
                          background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                          font=("Segoe UI", 9))
        label.pack(ipadx=5, ipady=2)
        self.tipwindow = tw

    def hide(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class TrimTab(ttk.Frame):
    """Вкладка обрезки медиафайлов с улучшенным UI и валидацией"""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._build_ui()

    def _build_ui(self):
        # Сетка
        for i in range(4):
            self.columnconfigure(i, weight=1)

        # Входной файл
        ttk.Label(self, text="Входной файл:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.input_ent = ttk.Entry(self)
        self.input_ent.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5)
        browse_in = ttk.Button(self, text="📂", width=3, command=self._browse_input)
        browse_in.grid(row=0, column=3, padx=5)
        ToolTip(self.input_ent, "Выберите видео или аудио файл для обрезки")
        ToolTip(browse_in, "Обзор входного файла")

        # Выходной файл
        ttk.Label(self, text="Выходной файл:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.output_ent = ttk.Entry(self)
        self.output_ent.grid(row=1, column=1, columnspan=2, sticky=tk.EW, padx=5)
        browse_out = ttk.Button(self, text="📁", width=3, command=self._browse_output)
        browse_out.grid(row=1, column=3, padx=5)
        ToolTip(self.output_ent, "Имя и путь для сохранения обрезанного файла")
        ToolTip(browse_out, "Обзор выходного файла")

        # Время начала
        ttk.Label(self, text="Старт (HH:MM:SS):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.start_var = tk.StringVar(value="00:00:00")
        self.start_ent = ttk.Entry(self, textvariable=self.start_var)
        self.start_ent.grid(row=2, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.start_ent, "Время начала обрезки")

        # Время окончания
        ttk.Label(self, text="Конец (HH:MM:SS):").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)
        self.end_var = tk.StringVar(value="00:00:10")
        self.end_ent = ttk.Entry(self, textvariable=self.end_var)
        self.end_ent.grid(row=2, column=3, sticky=tk.EW, padx=5)
        ToolTip(self.end_ent, "Время окончания обрезки")

        # Авточейн генерации имени
        gen_btn = ttk.Button(self, text="🔄", command=self._generate_name)
        gen_btn.grid(row=3, column=3, sticky=tk.E, padx=5, pady=(0,5))
        ToolTip(gen_btn, "Автозаполнить имя выходного файла")

        # Кнопка обрезки
        self.trim_btn = ttk.Button(self, text="✂️ Обрезать")
        self.trim_btn.grid(row=4, column=0, columnspan=4, pady=10)
        ToolTip(self.trim_btn, "Запустить обрезку медиафайла")

    def _browse_input(self):
        f = filedialog.askopenfilename(filetypes=[("Media", "*.mp4 *.mp3 *.mkv *.wav"), ("All", "*.*")])
        if f:
            self.input_ent.delete(0, tk.END)
            self.input_ent.insert(0, f)

    def _browse_output(self):
        f = filedialog.asksaveasfilename(defaultextension=".mp4",
                                         filetypes=[("MP4", "*.mp4"), ("All", "*.*")])
        if f:
            self.output_ent.delete(0, tk.END)
            self.output_ent.insert(0, f)

    def _generate_name(self):
        inp = self.input_ent.get().strip()
        st = self.start_var.get().strip()
        et = self.end_var.get().strip()
        if inp and is_valid_time_format(st) and is_valid_time_format(et):
            try:
                name = generate_trimmed_filename(inp, st, et)
                self.output_ent.delete(0, tk.END)
                self.output_ent.insert(0, name)
            except Exception:
                pass

    def get_input_path(self) -> str:
        return self.input_ent.get().strip()

    def get_output_path(self) -> str:
        return self.output_ent.get().strip()

    def get_start_time(self) -> str:
        return self.start_var.get().strip()

    def get_end_time(self) -> str:
        return self.end_var.get().strip()

    def set_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for widget in [self.input_ent, self.output_ent, self.start_ent, self.end_ent, self.trim_btn]:
            widget.configure(state=state)
