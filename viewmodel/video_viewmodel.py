import subprocess
from model.video_service import VideoService
from commands.trim_media import TrimMedia # Добавлено
# Import ProcessingContext only for type hints if needed, not for direct use here
# from model.processing_context import ProcessingContext
# Import constants only if needed for some VM logic, usually not required
# import constants
import os
from typing import List, Callable, Any, Optional, Dict
import queue
import traceback
import threading

# Type hint for listeners (typically the GUI's notification handler)
ViewModelListener = Callable[[Dict[str, Any]], None]

class VideoViewModel:
    """
    ViewModel, связывающий View (GUI) и Model (VideoService, TrimMedia).
    Управляет логикой оркестрации, состоянием и обменом данными через потокобезопасную очередь.
    """
    def __init__(self):
        """Инициализирует ViewModel, очередь сообщений, VideoService и TrimMedia."""
        self.message_queue = queue.Queue() # Потокобезопасная очередь для сообщений View
        self.listeners: List[ViewModelListener] = [] # Список слушателей (обычно GUI)
        # Сервис для обработки URL, передаем метод логирования в очередь
        self.service = VideoService(self._log_message_to_queue)
        # Команда обрезки, передаем тот же метод логирования
        self.trimmer = TrimMedia(self._log_message_to_queue)
        # Внутреннее состояние для предотвращения одновременного запуска одного типа операций
        self._is_url_processing = False
        self._url_processing_thread: Optional[threading.Thread] = None
        self._is_trimming = False
        self._trimming_thread: Optional[threading.Thread] = None


    def add_listener(self, listener: ViewModelListener):
        """Добавляет функцию-слушателя (например, _handle_vm_notification из GUI)."""
        if listener not in self.listeners:
            self.listeners.append(listener)

    def remove_listener(self, listener: ViewModelListener):
        """Удаляет функцию-слушателя."""
        try:
            self.listeners.remove(listener)
        except ValueError:
            pass

    def _notify_listeners(self, message: Dict[str, Any]):
        """
        Уведомляет всех зарегистрированных слушателей о событии.
        Может вызываться из рабочего потока, поэтому слушатели (GUI)
        должны обеспечивать безопасность потоков (например, используя `root.after` в Tkinter).
        Сообщение обычно сигнализирует о наличии новых данных в очереди.
        """
        for listener in self.listeners:
            try:
                listener(message)
            except Exception as e:
                print(f"ОШИБКА выполнения слушателя ViewModel {listener.__name__}: {e}", flush=True)
                print(traceback.format_exc(), flush=True)

    def _log_message_to_queue(self, msg: str, origin: str = "url"):
        """
        Логирует сообщение (из Model или VM), помещая его в очередь для View.
        Определяет уровень лога и добавляет источник (origin).
        """
        level = "INFO"
        msg_lower = msg.lower()
        # Определяем уровень по префиксам
        if msg_lower.startswith("[error]") or msg_lower.startswith("✖") or msg_lower.startswith("❌"):
             level = "ERROR"
        elif msg_lower.startswith("[warn]"):
             level = "WARN"
        elif msg_lower.startswith("▶") or msg_lower.startswith("✔") or msg_lower.startswith("🎉") or msg_lower.startswith("✅") or msg_lower.startswith("[info]"):
             level = "INFO"
        elif msg_lower.startswith("[debug]"):
             level = "DEBUG"
        # Добавляем специальный уровень для обрезки для GUI
        elif msg_lower.startswith("[trim]"):
             level = "TRIM"
             # Удаляем префикс [TRIM] из самого сообщения, так как уровень уже установлен
             if msg.startswith("[TRIM]"):
                 msg = msg[len("[TRIM]"):].lstrip()


        # Фильтруем DEBUG сообщения, если не включен режим отладки (условно)
        # if level == "DEBUG" and not constants.DEBUG_MODE: return

        log_event = {"type": "log", "level": level, "data": msg, "origin": origin}
        self.message_queue.put(log_event)
        # Уведомляем слушателей, что очередь обновилась
        self._notify_listeners({"type": "queue_update"})


    def run(self, url: str, yandex_audio: Optional[str], actions: List[str], output_dir: str, settings: Dict[str, Any]):
        """
        Запускает задачу обработки видео (VideoService.perform_actions) в отдельном потоке.
        """
        if self._is_url_processing and self._url_processing_thread and self._url_processing_thread.is_alive():
             self._log_message_to_queue("[WARN] Задача обработки URL уже выполняется.", origin="url")
             return
        if self._is_trimming and self._trimming_thread and self._trimming_thread.is_alive():
             self._log_message_to_queue("[WARN] Дождитесь завершения обрезки перед запуском обработки URL.", origin="url")
             return

        self._is_url_processing = True

        # Сигнал о начале в GUI через очередь
        self.message_queue.put({"type": "status", "level":"INFO", "data": "running", "origin": "url"})
        self._notify_listeners({"type": "queue_update"})

        # Целевая функция для фонового потока
        def task():
            success = False
            try:
                success = self.service.perform_actions(url, yandex_audio, actions, output_dir, settings)
            except Exception as e:
                error_msg = f"Критическая ошибка во время выполнения VideoService: {type(e).__name__} - {e}"
                self._log_message_to_queue(f"[ERROR] {error_msg}", origin="url")
                self._log_message_to_queue(f"[DEBUG] Traceback:\n{traceback.format_exc()}", origin="url")
                success = False
            finally:
                status = "finished" if success else "error"
                level = "INFO" if success else "ERROR"
                self.message_queue.put({"type": "status", "level": level, "data": status, "origin": "url"})
                self._notify_listeners({"type": "queue_update"})
                self._is_url_processing = False # Сброс флага

        self._url_processing_thread = threading.Thread(target=task, daemon=True)
        self._url_processing_thread.start()


    def run_trim(self, input_path: str, output_path: str, start_time: str, end_time: str):
        """
        Запускает задачу обрезки медиафайла (TrimMedia.execute) в отдельном потоке.
        """
        if self._is_trimming and self._trimming_thread and self._trimming_thread.is_alive():
            self._log_message_to_queue("[WARN] Задача обрезки уже выполняется.", origin="trim")
            return
        if self._is_url_processing and self._url_processing_thread and self._url_processing_thread.is_alive():
            self._log_message_to_queue("[WARN] Дождитесь завершения обработки URL перед запуском обрезки.", origin="trim")
            return

        self._is_trimming = True

        # Сигнал о начале в GUI
        self.message_queue.put({"type": "status", "level":"INFO", "data": "running", "origin": "trim"})
        self._notify_listeners({"type": "queue_update"})

        # Целевая функция для фонового потока обрезки
        def trim_task():
            success = False
            try:
                # Вызываем execute у экземпляра TrimMedia
                self.trimmer.execute(input_path, output_path, start_time, end_time)
                success = True # Если execute не вызвал исключение, считаем успехом
            except Exception as e:
                # Логируем ошибку через нашу систему (trimmer уже должен был залогировать детали)
                self._log_message_to_queue(f"[ERROR] Ошибка во время выполнения обрезки: {type(e).__name__} - {e}", origin="trim")
                # Дополнительно логируем traceback для неожиданных ошибок
                if not isinstance(e, (FileNotFoundError, ValueError, subprocess.CalledProcessError)):
                     self._log_message_to_queue(f"[DEBUG] Traceback:\n{traceback.format_exc()}", origin="trim")
                success = False
            finally:
                status = "finished" if success else "error"
                level = "INFO" if success else "ERROR"
                self.message_queue.put({"type": "status", "level": level, "data": status, "origin": "trim"})
                self._notify_listeners({"type": "queue_update"})
                self._is_trimming = False # Сброс флага

        self._trimming_thread = threading.Thread(target=trim_task, daemon=True)
        self._trimming_thread.start()


    def get_message_from_queue(self) -> Optional[Dict[str, Any]]:
        """
        Позволяет View (или другим слушателям) извлечь одно сообщение
        из очереди без блокировки.

        Returns:
            Словарь сообщения, если он доступен, иначе None.
        """
        try:
            return self.message_queue.get_nowait()
        except queue.Empty:
            return None