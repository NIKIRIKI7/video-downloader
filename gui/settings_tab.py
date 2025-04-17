import tkinter as tk
from tkinter import ttk
from typing import Dict, Any, List

import constants  # Для значений по умолчанию


class SettingsTab(ttk.Frame):
    """Класс для вкладки настроек."""

    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)
        self._create_widgets()

    def _create_widgets(self):
        """Создает виджеты на вкладке настроек."""
        settings_frame = ttk.Frame(self, padding=15)
        settings_frame.pack(fill=tk.BOTH, expand=True)
        settings_frame.columnconfigure(1, weight=1)

        current_row = 0

        # -- Языки и субтитры --
        lang_frame = ttk.LabelFrame(settings_frame, text="Языки и субтитры", padding=10)
        lang_frame.grid(row=current_row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        lang_frame.columnconfigure(1, weight=0)
        current_row += 1

        ttk.Label(lang_frame, text="Исходный язык (Перевод С):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.source_lang_var = tk.StringVar(value=constants.SOURCE_LANG_DEFAULT)
        self.source_lang_ent = ttk.Entry(lang_frame, textvariable=self.source_lang_var, width=10)
        self.source_lang_ent.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(lang_frame, text="Целевой язык (Перевод НА):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.target_lang_var = tk.StringVar(value=constants.TARGET_LANG_DEFAULT)
        self.target_lang_ent = ttk.Entry(lang_frame, textvariable=self.target_lang_var, width=10)
        self.target_lang_ent.grid(row=1, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(lang_frame, text="Язык скачивания субтитров:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.subtitle_lang_var = tk.StringVar(value=constants.SUB_LANG_DEFAULT)
        self.subtitle_lang_ent = ttk.Entry(lang_frame, textvariable=self.subtitle_lang_var, width=10)
        self.subtitle_lang_ent.grid(row=2, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(lang_frame, text="Формат субтитров (vtt, srt):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=3)
        self.subtitle_format_var = tk.StringVar(value=constants.SUB_FORMAT_DEFAULT)
        self.subtitle_format_ent = ttk.Entry(lang_frame, textvariable=self.subtitle_format_var, width=10)
        self.subtitle_format_ent.grid(row=3, column=1, sticky=tk.W, padx=5, pady=3)

        # -- Микширование аудио (FFmpeg) --
        audio_frame = ttk.LabelFrame(settings_frame, text="Микширование аудио (FFmpeg)", padding=10)
        audio_frame.grid(row=current_row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        audio_frame.columnconfigure(1, weight=0)
        current_row += 1

        ttk.Label(audio_frame, text="Громкость оригинала (0.0=Тихо, 1.0=Исходная):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.original_volume_var = tk.StringVar(value=constants.ORIGINAL_VOLUME_DEFAULT)
        self.original_volume_ent = ttk.Entry(audio_frame, textvariable=self.original_volume_var, width=10)
        self.original_volume_ent.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(audio_frame, text="Громкость добавленного аудио (1.0=Исходная):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.added_volume_var = tk.StringVar(value=constants.ADDED_VOLUME_DEFAULT)
        self.added_volume_ent = ttk.Entry(audio_frame, textvariable=self.added_volume_var, width=10)
        self.added_volume_ent.grid(row=1, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(audio_frame, text="Аудио кодек после слияния (aac, mp3):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.merged_audio_codec_var = tk.StringVar(value=constants.MERGED_AUDIO_CODEC_DEFAULT)
        self.merged_audio_codec_ent = ttk.Entry(audio_frame, textvariable=self.merged_audio_codec_var, width=10)
        self.merged_audio_codec_ent.grid(row=2, column=1, sticky=tk.W, padx=5, pady=3)

        # -- Скачивание (yt-dlp) --
        dl_frame = ttk.LabelFrame(settings_frame, text="Скачивание (yt-dlp)", padding=10)
        dl_frame.grid(row=current_row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        dl_frame.columnconfigure(1, weight=1)
        current_row += 1

        ttk.Label(dl_frame, text="Код формата видео (см. yt-dlp -F):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.yt_dlp_format_var = tk.StringVar(value=constants.YT_DLP_FORMAT_DEFAULT)
        self.yt_dlp_format_ent = ttk.Entry(dl_frame, textvariable=self.yt_dlp_format_var, width=50)
        self.yt_dlp_format_ent.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=3)

        ttk.Label(dl_frame, text="Контейнер видео на выходе (mp4, mkv):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.video_format_ext_var = tk.StringVar(value=constants.VIDEO_FORMAT_EXT_DEFAULT)
        self.video_format_ext_ent = ttk.Entry(dl_frame, textvariable=self.video_format_ext_var, width=10)
        self.video_format_ext_ent.grid(row=1, column=1, sticky=tk.W, padx=5, pady=3)

        # Список всех полей ввода для управления состоянием
        self.input_widgets = [
            self.source_lang_ent, self.target_lang_ent, self.subtitle_lang_ent,
            self.subtitle_format_ent, self.original_volume_ent, self.added_volume_ent,
            self.merged_audio_codec_ent, self.yt_dlp_format_ent, self.video_format_ext_ent
        ]

    def get_settings(self) -> Dict[str, Any]:
        """Собирает текущие настройки со вкладки."""
        settings = {
            'source_lang': self.source_lang_var.get().strip().lower(),
            'target_lang': self.target_lang_var.get().strip().lower(),
            'subtitle_lang': self.subtitle_lang_var.get().strip().lower(),
            'subtitle_format': self.subtitle_format_var.get().strip().lower(),
            'original_volume': self.original_volume_var.get().strip(),
            'added_volume': self.added_volume_var.get().strip(),
            'merged_audio_codec': self.merged_audio_codec_var.get().strip().lower(),
            'yt_dlp_format': self.yt_dlp_format_var.get().strip(),
            'video_format_ext': self.video_format_ext_var.get().strip().lower(),
        }
        # Санитизация расширений (удаление ведущей точки)
        settings['video_format_ext'] = settings['video_format_ext'].lstrip('.')
        settings['subtitle_format'] = settings['subtitle_format'].lstrip('.')
        return settings

    def set_enabled(self, enabled: bool):
        """Включает или отключает поля ввода на вкладке."""
        widget_state = 'normal' if enabled else 'disabled'
        for widget in self.input_widgets:
            try:
                widget.configure(state=widget_state)
            except tk.TclError:
                pass # Игнорировать ошибки для уже уничтоженных виджетов