# File: viewmodel/video_viewmodel.py

from model.video_service import VideoService
# Добавляем Dict в импорт
from typing import List, Callable, Any, Optional, Dict
import queue
import traceback # Добавим импорт traceback здесь, т.к. он используется

# Тип для подписчика ViewModel (может принимать разные типы сообщений)
ViewModelListener = Callable[[Dict[str, Any]], None]

class VideoViewModel:
    """
    ViewModel для управления логикой видео-операций и связи с View.
    """
    def __init__(self):
        """Инициализатор ViewModel."""
        # Используем потокобезопасную очередь для сообщений в GUI
        self.message_queue = queue.Queue()
        self.listeners: List[ViewModelListener] = []
        # Сервис создается здесь, передаем ему метод log через очередь
        self.service = VideoService(self._log_message)

    def add_listener(self, listener: ViewModelListener):
        """
        Добавляет подписчика на обновления от ViewModel.

        Args:
            listener: Функция обратного вызова, которая будет вызываться
                      при поступлении новых сообщений (например, логов, статуса).
                      Ожидает словарь с ключами 'type' ('log', 'status') и 'data'.
        """
        if listener not in self.listeners:
            self.listeners.append(listener)

    def remove_listener(self, listener: ViewModelListener):
        """Удаляет подписчика."""
        try:
            self.listeners.remove(listener)
        except ValueError:
            pass # Игнорируем, если подписчика уже нет

    def _notify_listeners(self, message: Dict[str, Any]):
        """Уведомляет всех подписчиков о событии."""
        for listener in self.listeners:
            try:
                listener(message)
            except Exception as e:
                # Логируем ошибку в самом подписчике, чтобы не сломать цикл
                # Используем print, так как логгер ViewModel может быть недоступен или вызывать зацикливание
                print(f"Ошибка в подписчике ViewModel: {e}")
                print(traceback.format_exc())

    def _log_message(self, msg: str):
        """
        Метод для логирования, который будет передан в VideoService.
        Помещает лог-сообщение в очередь для потокобезопасной передачи в GUI.
        """
        log_event = {"type": "log", "data": msg}
        # Кладем в очередь
        self.message_queue.put(log_event)
        # Уведомляем GUI, что есть что-то в очереди (GUI сам решит, как прочитать)
        # Этот вызов _notify_listeners может происходить из рабочего потока service!
        # Поэтому _notify_listeners должен быть потокобезопасным или вызываться из основного потока
        # В текущей реализации gui.py он вызывает root.after(0, ...), что безопасно.
        self._notify_listeners({"type": "queue_update"})


    def run(self, url: str, yandex_audio: Optional[str], actions: List[str]):
        """
        Запускает выполнение выбранных действий через VideoService.
        Этот метод выполняется в отдельном потоке (см. gui.py).

        Args:
            url: URL видео.
            yandex_audio: Путь к аудиофайлу Yandex (может быть None).
            actions: Список ключей действий.
        """
        # Сообщаем GUI о начале операции через очередь
        self.message_queue.put({"type": "status", "data": "running"})
        self._notify_listeners({"type": "queue_update"})

        success = False
        try:
            # Вызываем сервис для выполнения работы
            success = self.service.perform_actions(url, yandex_audio, actions)

        except Exception as e:
            # Ловим любые ошибки, которые могли произойти на уровне сервиса
            # (хотя VideoService уже должен был их обработать и залогировать)
            error_msg = f"Критическая ошибка в VideoService: {type(e).__name__} - {e}"
            # Используем _log_message, который кладет в очередь
            self._log_message(f"❌ {error_msg}")
            self._log_message(f"Traceback:\n{traceback.format_exc()}")
            success = False
        finally:
            # Сообщаем GUI о завершении операции (успешном или нет) через очередь
            status = "finished" if success else "error"
            self.message_queue.put({"type": "status", "data": status})
            self._notify_listeners({"type": "queue_update"})

    def get_message_from_queue(self) -> Optional[Dict[str, Any]]:
        """
        Извлекает одно сообщение из очереди (неблокирующий вызов).
        Предназначен для использования View в основном потоке.

        Returns:
            Словарь сообщения или None, если очередь пуста.
        """
        try:
            return self.message_queue.get_nowait()
        except queue.Empty:
            return None