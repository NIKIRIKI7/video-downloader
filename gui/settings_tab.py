# File: gui/settings_tab.py

import tkinter as tk
from tkinter import ttk
from typing import Any, Dict
import constants
from utils.utils import is_valid_time_format

# Простой класс тултипов (копия из process_tab)
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

class SettingsTab(ttk.Frame):
    """Вкладка Настройки: языки, форматы и громкость"""
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._build_ui()

    def _build_ui(self):
        # Настройка grid
        for i in range(2): self.columnconfigure(i, weight=1)

        # Исходный язык
        ttk.Label(self, text="Исходный язык:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.source_lang_var = tk.StringVar(value=constants.SOURCE_LANG_DEFAULT)
        self.source_lang_ent = ttk.Entry(self, textvariable=self.source_lang_var)
        self.source_lang_ent.grid(row=0, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.source_lang_ent, "Код языка оригинала (напр. en, ru, pt-br)")

        # Целевой язык
        ttk.Label(self, text="Целевой язык:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.target_lang_var = tk.StringVar(value=constants.TARGET_LANG_DEFAULT)
        self.target_lang_ent = ttk.Entry(self, textvariable=self.target_lang_var)
        self.target_lang_ent.grid(row=1, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.target_lang_ent, "Код языка перевода (напр. ru, en)")

        # Язык субтитров
        ttk.Label(self, text="Язык субтитров:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.subtitle_lang_var = tk.StringVar(value=constants.SUB_LANG_DEFAULT)
        self.subtitle_lang_ent = ttk.Entry(self, textvariable=self.subtitle_lang_var)
        self.subtitle_lang_ent.grid(row=2, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.subtitle_lang_ent, "Код языка для загрузки субтитров (напр. en)")

        # Формат субтитров
        ttk.Label(self, text="Формат субтитров:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.subtitle_format_var = tk.StringVar(value=constants.SUB_FORMAT_DEFAULT)
        self.subtitle_format_ent = ttk.Entry(self, textvariable=self.subtitle_format_var)
        self.subtitle_format_ent.grid(row=3, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.subtitle_format_ent, "Расширение субтитров (напр. vtt, srt)")

        # Формат видео
        ttk.Label(self, text="Формат видео (yt-dlp):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.yt_dlp_format_var = tk.StringVar(value=constants.YT_DLP_FORMAT_DEFAULT)
        self.yt_dlp_format_ent = ttk.Entry(self, textvariable=self.yt_dlp_format_var)
        self.yt_dlp_format_ent.grid(row=4, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.yt_dlp_format_ent, "Шаблон формата yt-dlp (напр. bestvideo+bestaudio)")

        # Контейнер видео
        ttk.Label(self, text="Контейнер видео:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.video_format_ext_var = tk.StringVar(value=constants.VIDEO_FORMAT_EXT_DEFAULT)
        self.video_format_ext_ent = ttk.Entry(self, textvariable=self.video_format_ext_var)
        self.video_format_ext_ent.grid(row=5, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.video_format_ext_ent, "Расширение видео после слияния (напр. mp4)")

        # Громкость оригинала
        ttk.Label(self, text="Громкость оригинала:").grid(row=6, column=0, sticky=tk.W, padx=5, pady=5)
        self.original_volume_var = tk.StringVar(value=constants.ORIGINAL_VOLUME_DEFAULT)
        self.original_volume_ent = ttk.Entry(self, textvariable=self.original_volume_var)
        self.original_volume_ent.grid(row=6, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.original_volume_ent, "Громкость исходного аудио (0.0-1.0)")

        # Громкость добавленного
        ttk.Label(self, text="Громкость перевода:").grid(row=7, column=0, sticky=tk.W, padx=5, pady=5)
        self.added_volume_var = tk.StringVar(value=constants.ADDED_VOLUME_DEFAULT)
        self.added_volume_ent = ttk.Entry(self, textvariable=self.added_volume_var)
        self.added_volume_ent.grid(row=7, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.added_volume_ent, "Громкость добавленного аудио (0.0-1.0)")

        # Кодек смешения
        ttk.Label(self, text="Аудио кодек:").grid(row=8, column=0, sticky=tk.W, padx=5, pady=5)
        self.merged_audio_codec_var = tk.StringVar(value=constants.MERGED_AUDIO_CODEC_DEFAULT)
        self.merged_audio_codec_ent = ttk.Entry(self, textvariable=self.merged_audio_codec_var)
        self.merged_audio_codec_ent.grid(row=8, column=1, sticky=tk.EW, padx=5)
        ToolTip(self.merged_audio_codec_ent, "Кодек для смешанного аудио (напр. aac)")

    def get_settings(self) -> Dict[str, Any]:
        settings = {
            'source_lang': self.source_lang_var.get().strip(),
            'target_lang': self.target_lang_var.get().strip(),
            'subtitle_lang': self.subtitle_lang_var.get().strip(),
            'subtitle_format': self.subtitle_format_var.get().strip(),
            'yt_dlp_format': self.yt_dlp_format_var.get().strip(),
            'video_format_ext': self.video_format_ext_var.get().strip(),
            'original_volume': self.original_volume_var.get().strip(),
            'added_volume': self.added_volume_var.get().strip(),
            'merged_audio_codec': self.merged_audio_codec_var.get().strip(),
        }
        # Sanitize
        settings['video_format_ext'] = settings['video_format_ext'].lstrip('.')
        settings['subtitle_format'] = settings['subtitle_format'].lstrip('.')
        return settings

    def set_enabled(self, enabled: bool) -> None:
        state = tk.NORMAL if enabled else tk.DISABLED
        for widget in [
            self.source_lang_ent, self.target_lang_ent,
            self.subtitle_lang_ent, self.subtitle_format_ent,
            self.yt_dlp_format_ent, self.video_format_ext_ent,
            self.original_volume_ent, self.added_volume_ent,
            self.merged_audio_codec_ent
        ]:
            widget.configure(state=state)
