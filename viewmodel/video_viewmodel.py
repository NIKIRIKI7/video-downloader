# File: viewmodel/video_viewmodel.py

import subprocess
import threading
import traceback
import queue
from pathlib import Path
from typing import List, Callable, Any, Optional, Dict

from model.video_service import VideoService
from commands.trim_media import TrimMedia

# Тип для слушателей (GUI)
ViewModelListener = Callable[[Dict[str, Any]], None]

class VideoViewModel:
    """
    ViewModel, связывающий GUI и модели обработки (VideoService, TrimMedia).
    Управляет потоками, очередью сообщений и уведомляет GUI.
    """
    def __init__(self):
        # Очередь сообщений для логов и статусов
        self.message_queue: queue.Queue = queue.Queue()
        self.listeners: List[ViewModelListener] = []

        # Сервис для обработки URL и команда обрезки
        self.service = VideoService(self._log_message_to_queue)
        self.trimmer = TrimMedia(self._log_message_to_queue)

        # Флаги состояния и ссылки на потоки
        self._is_url_processing: bool = False
        self._url_thread: Optional[threading.Thread] = None
        self._is_trimming: bool = False
        self._trim_thread: Optional[threading.Thread] = None

    def add_listener(self, listener: ViewModelListener) -> None:
        if listener not in self.listeners:
            self.listeners.append(listener)

    def remove_listener(self, listener: ViewModelListener) -> None:
        if listener in self.listeners:
            self.listeners.remove(listener)

    def _notify_listeners(self, msg: Dict[str, Any]) -> None:
        for listener in list(self.listeners):
            try:
                listener(msg)
            except Exception:
                pass

    def _log_message_to_queue(self, msg: str, origin: str = "url") -> None:
        # Определяем уровень по префиксам
        level = "INFO"
        m = msg.lower()
        if m.startswith("[error]") or m.startswith("❌"):
            level = "ERROR"
        elif m.startswith("[warn]"):
            level = "WARN"
        elif m.startswith("[debug]"):
            level = "DEBUG"
        elif m.startswith("[trim]"):
            level = "TRIM"

        event = {"type": "log", "level": level, "data": msg, "origin": origin}
        self.message_queue.put(event)
        self._notify_listeners({"type": "queue_update"})

    def get_message_from_queue(self) -> Optional[Dict[str, Any]]:
        try:
            return self.message_queue.get_nowait()
        except queue.Empty:
            return None

    def run(self,
            url: str,
            yandex_audio: Optional[str],
            actions: List[str],
            output_dir: str,
            settings: Dict[str, Any]) -> None:
        """
        Запускает обработку URL в фоне: создаёт ProcessingContext и вызывает VideoService.perform_actions.
        Преобразует пути в pathlib.Path.
        """
        if self._is_url_processing:
            self._log_message_to_queue("[WARN] URL-обработка уже запущена.", origin="url")
            return
        if self._is_trimming:
            self._log_message_to_queue("[WARN] Дождитесь завершения обрезки перед обработкой URL.", origin="url")
            return

        self._is_url_processing = True
        # Сигнал GUI о старте
        self.message_queue.put({"type": "status", "level": "INFO", "data": "running", "origin": "url"})
        self._notify_listeners({"type": "queue_update"})

        def task():
            success = False
            try:
                ya_path = Path(yandex_audio) if yandex_audio else None
                out_dir = Path(output_dir)
                success = self.service.perform_actions(url, ya_path, actions, out_dir, settings)
            except Exception as e:
                self._log_message_to_queue(f"[ERROR] Сервис завершился с ошибкой: {e}", origin="url")
                self._log_message_to_queue(f"[DEBUG] Traceback:\n{traceback.format_exc()}", origin="url")
            finally:
                status = "finished" if success else "error"
                level = "INFO" if success else "ERROR"
                self.message_queue.put({"type": "status", "level": level, "data": status, "origin": "url"})
                self._notify_listeners({"type": "queue_update"})
                self._is_url_processing = False

        self._url_thread = threading.Thread(target=task, daemon=True)
        self._url_thread.start()

    def run_trim(self,
                 input_path: str,
                 output_path: str,
                 start_time: str,
                 end_time: str) -> None:
        """
        Запускает задачу обрезки файла во фоновом потоке.
        Преобразует пути в pathlib.Path.
        """
        if self._is_trimming:
            self._log_message_to_queue("[WARN] Обрезка уже запущена.", origin="trim")
            return
        if self._is_url_processing:
            self._log_message_to_queue("[WARN] Дождитесь завершения URL-обработки перед обрезкой.", origin="trim")
            return

        self._is_trimming = True
        self.message_queue.put({"type": "status", "level": "INFO", "data": "running", "origin": "trim"})
        self._notify_listeners({"type": "queue_update"})

        def trim_task():
            success = False
            try:
                in_path = Path(input_path)
                out_path = Path(output_path)
                self.trimmer.execute(in_path, out_path, start_time, end_time)
                success = True
            except Exception as e:
                self._log_message_to_queue(f"[ERROR] Обрезка завершилась с ошибкой: {e}", origin="trim")
                if not isinstance(e, (FileNotFoundError, ValueError, subprocess.CalledProcessError)):
                    self._log_message_to_queue(f"[DEBUG] Traceback:\n{traceback.format_exc()}", origin="trim")
            finally:
                status = "finished" if success else "error"
                level = "INFO" if success else "ERROR"
                self.message_queue.put({"type": "status", "level": level, "data": status, "origin": "trim"})
                self._notify_listeners({"type": "queue_update"})
                self._is_trimming = False

        self._trim_thread = threading.Thread(target=trim_task, daemon=True)
        self._trim_thread.start()
