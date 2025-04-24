# File: gui/process_tab.py

import tkinter as tk
from tkinter import ttk, filedialog
from typing import Dict, List, Optional
import constants
from utils.utils import ensure_dir

# Простой класс для тултипов
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
        self.tipwindow = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = ttk.Label(tw, text=self.text, justify=tk.LEFT,
                          background="#ffffe0", relief=tk.SOLID, borderwidth=1,
                          font=("Segoe UI", 9))
        label.pack(ipadx=5, ipady=2)

    def hide(self, event=None):
        tw = self.tipwindow
        self.tipwindow = None
        if tw:
            tw.destroy()

class ProcessTab(ttk.Frame):
    """Вкладка обработки URL: выбор действий, логирование и управление."""
    ACTION_DEFINITIONS = [
        ('tp', 'Скачать превью'),
        ('md', 'Метаданные'),
        ('dv', 'Видео'),
        ('ds', 'Субтитры'),
        ('dt', 'Перевод субтитров'),
        ('da', 'Смешать аудио'),
        ('tm', 'Перевод метаданных'),
    ]

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self.action_vars: Dict[str, tk.BooleanVar] = {}
        self._build_ui()

    def _build_ui(self):
        # Сетка для адаптивности
        self.columnconfigure(1, weight=1)

        # URL
        ttk.Label(self, text="URL видео:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.url_ent = ttk.Entry(self)
        self.url_ent.grid(row=0, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.url_ent, "Вставьте полный URL видео https://... .")

        # Аудио
        ttk.Label(self, text="Yandex Audio:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.y_ent = ttk.Entry(self)
        self.y_ent.grid(row=1, column=1, sticky=tk.EW, padx=5)
        self.browse_y_btn = ttk.Button(self, text="📂", width=3, command=self._browse_y)
        self.browse_y_btn.grid(row=1, column=2, padx=5)
        ToolTip(self.browse_y_btn, "Выберите файл аудио от Yandex Translate.")

        # Папка вывода
        ttk.Label(self, text="Папка вывода:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.out_dir_var = tk.StringVar(value=constants.VIDEO_DIR_DEFAULT)
        self.out_dir_ent = ttk.Entry(self, textvariable=self.out_dir_var)
        self.out_dir_ent.grid(row=2, column=1, sticky=tk.EW, padx=5)
        self.browse_out_btn = ttk.Button(self, text="📁", width=3, command=self._browse_out)
        self.browse_out_btn.grid(row=2, column=2, padx=5)
        ToolTip(self.browse_out_btn, "Выберите папку для сохранения результатов.")

        # Действия
        actions_frame = ttk.LabelFrame(self, text="Действия")
        actions_frame.grid(row=3, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=10)
        for i, (key, label) in enumerate(self.ACTION_DEFINITIONS):
            var = tk.BooleanVar(value=False)
            cb = ttk.Checkbutton(actions_frame, text=label, variable=var)
            cb.grid(row=i//4, column=i%4, padx=5, pady=3, sticky=tk.W)
            self.action_vars[key] = var

        # Лог
        log_frame = ttk.LabelFrame(self, text="Лог")
        log_frame.grid(row=4, column=0, columnspan=3, sticky=tk.NSEW, padx=5, pady=5)
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        self.log_txt = tk.Text(log_frame, height=10, wrap=tk.NONE)
        self.log_txt.grid(row=0, column=0, sticky=tk.NSEW)
        self.log_txt.configure(state=tk.DISABLED)

        # Кнопки управления
        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=5, column=0, columnspan=3, pady=10)
        self.start_btn = ttk.Button(btn_frame, text="▶ Запустить")
        self.start_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.start_btn, "Запустить выбранные действия.")
        self.clear_log_btn = ttk.Button(btn_frame, text="🗑 Очистить лог")
        self.clear_log_btn.pack(side=tk.LEFT, padx=5)
        ToolTip(self.clear_log_btn, "Очистить окно лога.")

    def _browse_y(self):
        file = filedialog.askopenfilename(filetypes=[("Audio", "*.mp3 *.m4a"), ("All", "*.*")])
        if file: self.y_ent.delete(0, tk.END); self.y_ent.insert(0, file)

    def _browse_out(self):
        dir = filedialog.askdirectory()
        if dir: self.out_dir_var.set(dir)

    def get_url(self) -> str:
        return self.url_ent.get().strip()

    def get_yandex_audio(self) -> str:
        return self.y_ent.get().strip()

    def get_output_dir(self) -> str:
        return self.out_dir_var.get().strip()

    def get_selected_actions(self) -> List[str]:
        return [k for k,v in self.action_vars.items() if v.get()]

    def add_log_message(self, msg: str, level: str = 'INFO') -> None:
        self.log_txt.configure(state=tk.NORMAL)
        self.log_txt.insert(tk.END, f"[{level}] {msg}\n")
        self.log_txt.see(tk.END)
        self.log_txt.configure(state=tk.DISABLED)

    def clear_log(self) -> None:
        self.log_txt.configure(state=tk.NORMAL)
        self.log_txt.delete('1.0', tk.END)
        self.log_txt.configure(state=tk.DISABLED)
