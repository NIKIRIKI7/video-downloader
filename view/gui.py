import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import queue # Импортируем очередь
from viewmodel.video_viewmodel import VideoViewModel
from typing import Dict, Any

class VideoAppGUI:
    """
    Класс для создания и управления графическим интерфейсом пользователя (GUI)
    приложения для обработки видео.
    """
    QUEUE_POLL_INTERVAL_MS = 100 # Интервал проверки очереди ViewModel (в миллисекундах)

    def __init__(self, root: tk.Tk, view_model: VideoViewModel):
        """
        Инициализирует GUI.

        Args:
            root: Корневое окно Tkinter.
            view_model: Экземпляр ViewModel.
        """
        self.root = root
        self.vm = view_model
        self.vm.add_listener(self._handle_vm_notification) # Подписываемся на уведомления VM

        self.root.title("Video App MVVM (Исправленная версия)")
        self.root.geometry("700x550") # Немного увеличим окно

        # Стили ttk для улучшения внешнего вида (опционально)
        style = ttk.Style()
        style.theme_use('clam') # Попробуем другую тему

        # --- Создание виджетов ---
        frm = ttk.Frame(self.root, padding=15)
        frm.pack(fill=tk.BOTH, expand=True)

        # URL entry
        ttk.Label(frm, text="Video URL:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.url_ent = ttk.Entry(frm, width=60) # Увеличим ширину поля
        self.url_ent.grid(row=0, column=1, columnspan=3, sticky=tk.EW, pady=2)
        frm.columnconfigure(1, weight=1) # Позволяем полю URL растягиваться

        # Yandex audio
        ttk.Label(frm, text="Yandex Audio (MP3):").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.y_ent = ttk.Entry(frm, width=50)
        self.y_ent.grid(row=1, column=1, sticky=tk.EW, pady=2)
        self.browse_btn = ttk.Button(frm, text="Browse...", command=self._browse_yandex_audio)
        self.browse_btn.grid(row=1, column=2, padx=(5, 0), pady=2)

        # Actions
        actions_frame = ttk.LabelFrame(frm, text=" Действия ", padding=10)
        actions_frame.grid(row=2, column=0, columnspan=4, pady=10, sticky=tk.EW)
        self.action_vars: Dict[str, tk.BooleanVar] = {}
        # Определяем действия и их описания
        action_definitions = [
            ('md', '1. Скачать метаданные (ID, Название, Описание)'),
            ('dv', '2. Скачать видео (MP4)'),
            ('ds', '3. Скачать субтитры (EN, VTT)'),
            ('dt', '4. Перевести субтитры (RU, VTT)'),
            ('da', '5. Смешать аудио (с Yandex Audio)')
            # ('tm', 'Translate Metadata'), # Можно добавить чекбокс и сюда
        ]
        # Размещаем чекбоксы динамически
        rows = 2
        cols = 3
        for i, (key, label) in enumerate(action_definitions):
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(actions_frame, text=label, variable=var)
            # Используем grid для более гибкого размещения
            cb.grid(row=i // cols, column=i % cols, padx=5, pady=3, sticky=tk.W)
            self.action_vars[key] = var

        # Log Area
        log_frame = ttk.LabelFrame(frm, text=" Лог выполнения ", padding=5)
        log_frame.grid(row=3, column=0, columnspan=4, pady=(5, 5), sticky=tk.NSEW)
        self.log_txt = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, state=tk.DISABLED) # Изначально выключен для редактирования
        self.log_txt.pack(fill=tk.BOTH, expand=True)
        frm.rowconfigure(3, weight=1) # Позволяем логу растягиваться по вертикали

        # Progress Bar
        self.progress = ttk.Progressbar(frm, mode='indeterminate')
        self.progress.grid(row=4, column=0, columnspan=4, pady=5, sticky=tk.EW)

        # Start Button
        self.start_btn = ttk.Button(frm, text="Начать", command=self._on_start)
        self.start_btn.grid(row=5, column=0, columnspan=4, pady=(10, 0))

        # Переменная для хранения состояния выполнения
        self._is_running = False

        # Запускаем цикл проверки очереди ViewModel
        self.root.after(self.QUEUE_POLL_INTERVAL_MS, self._check_vm_queue)

    def _browse_yandex_audio(self):
        """Открывает диалог выбора файла MP3 и вставляет путь в поле."""
        filename = filedialog.askopenfilename(
            title="Выберите MP3 файл Yandex Audio",
            filetypes=[("MP3 audio", "*.mp3"), ("All files", "*.*")]
        )
        if filename:
            self.y_ent.delete(0, tk.END)
            self.y_ent.insert(0, filename)

    def _set_controls_state(self, enabled: bool):
        """Включает или выключает элементы управления."""
        state = tk.NORMAL if enabled else tk.DISABLED
        self.url_ent.config(state=state)
        self.y_ent.config(state=state)
        self.browse_btn.config(state=state)
        self.start_btn.config(state=state)
        for var in self.action_vars.values():
            # Находим виджет Checkbutton по переменной (немного хак, но работает)
            # Лучше было бы хранить ссылки на сами чекбоксы
            for cb in self.root.winfo_children(): # Ищем во всех виджетах (не очень эффективно)
                 if isinstance(cb, ttk.Frame): # Ищем во фреймах
                     for w in cb.winfo_children():
                         if isinstance(w, ttk.LabelFrame): # Ищем в LabelFrame
                             for widget in w.winfo_children():
                                if isinstance(widget, ttk.Checkbutton) and widget.cget('variable') == str(var):
                                     widget.config(state=state)
                                     break # Нашли нужный чекбокс

    def _add_log_message(self, message: str):
        """Добавляет сообщение в текстовое поле лога."""
        self.log_txt.config(state=tk.NORMAL) # Включаем для записи
        self.log_txt.insert(tk.END, message + "\n")
        self.log_txt.see(tk.END) # Автопрокрутка вниз
        self.log_txt.config(state=tk.DISABLED) # Выключаем обратно

    def _on_start(self):
        """Обработчик нажатия кнопки 'Начать'."""
        if self._is_running:
            return # Не запускать, если уже выполняется

        url = self.url_ent.get().strip()
        yandex_audio_path = self.y_ent.get().strip()
        selected_actions = [key for key, var in self.action_vars.items() if var.get()]

        # --- Валидация ввода ---
        if not url:
            messagebox.showerror("Ошибка ввода", "Необходимо указать URL видео.")
            return
        if not selected_actions:
            messagebox.showerror("Ошибка ввода", "Необходимо выбрать хотя бы одно действие.")
            return
        if 'da' in selected_actions and not yandex_audio_path:
             messagebox.showerror("Ошибка ввода", "Для действия 'Смешать аудио' необходимо указать путь к файлу Yandex Audio.")
             return
        if 'da' in selected_actions and yandex_audio_path and not yandex_audio_path.lower().endswith(".mp3"):
             messagebox.showwarning("Предупреждение", "Выбранный файл Yandex Audio не имеет расширения .mp3. Убедитесь, что это корректный аудиофайл.")
             # Не прерываем, но предупреждаем

        # --- Запуск операции ---
        self._is_running = True
        self._set_controls_state(enabled=False) # Блокируем интерфейс
        self.progress.start(10) # Запускаем индикатор прогресса
        self._add_log_message("=" * 40)
        self._add_log_message(">>> Операция начата...")

        # Запускаем выполнение в отдельном потоке, чтобы не блокировать GUI
        threading.Thread(
            target=self.vm.run,
            args=(url, yandex_audio_path, selected_actions),
            daemon=True # Поток завершится, если закроется основное приложение
        ).start()

    def _handle_vm_notification(self, message: Dict[str, Any]):
        """
        Обработчик уведомлений от ViewModel.
        В данном случае, просто сигнализирует, что нужно проверить очередь.
        Вызывается из потока ViewModel! Не обновляем GUI напрямую здесь.
        """
        if message.get("type") == "queue_update":
            # Просто планируем проверку очереди в главном потоке Tkinter
            # Это гарантирует, что _check_vm_queue выполнится в правильном потоке
            self.root.after(0, self._check_vm_queue) # 0ms - выполнить как можно скорее

    def _check_vm_queue(self):
        """
        Проверяет очередь сообщений от ViewModel и обновляет GUI.
        Выполняется в основном потоке Tkinter благодаря root.after().
        """
        try:
            # Обрабатываем все сообщения в очереди за один раз
            while True:
                message = self.vm.get_message_from_queue()
                if message is None:
                    break # Очередь пуста

                msg_type = message.get("type")
                msg_data = message.get("data")

                if msg_type == "log":
                    self._add_log_message(str(msg_data))
                elif msg_type == "status":
                    if msg_data == "running":
                        # Дополнительные действия при старте (уже сделаны в _on_start)
                        pass
                    elif msg_data == "finished" or msg_data == "error":
                        # Операция завершена (успешно или с ошибкой)
                        self.progress.stop()
                        self._set_controls_state(enabled=True) # Разблокируем интерфейс
                        self._is_running = False
                        result_message = "✅ Операция успешно завершена." if msg_data == "finished" else "❌ Операция завершена с ошибкой."
                        self._add_log_message(f">>> {result_message}")
                        self._add_log_message("=" * 40)
                        if msg_data == "error":
                             messagebox.showerror("Ошибка выполнения", "Во время операции произошла ошибка. Подробности смотрите в логе.")
                        else:
                             messagebox.showinfo("Завершено", "Операция успешно выполнена.")

        except Exception as e:
             # Лог ошибки обработки очереди (не должно происходить)
             print(f"Ошибка при обработке очереди ViewModel: {e}")
             import traceback
             print(traceback.format_exc())

        # # Перепланируем следующую проверку очереди, только если не выполняется
        # # Нет, нужно проверять всегда, чтобы ловить сообщения об окончании
        # # if not self._is_running:
        # self.root.after(self.QUEUE_POLL_INTERVAL_MS, self._check_vm_queue)
        # Вместо перепланировки здесь, будем полагаться на _handle_vm_notification,
        # который вызывает _check_vm_queue через root.after(0, ...) при поступлении новых сообщений.
        # Это более реактивный подход.

# --- Функция для запуска GUI ---
def create_gui():
    """Создает и запускает главный цикл GUI."""
    root = tk.Tk()
    vm = VideoViewModel()
    app = VideoAppGUI(root, vm)
    root.mainloop()