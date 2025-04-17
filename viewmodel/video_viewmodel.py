from model.video_service import VideoService
from model.processing_context import ProcessingContext # Can be useful for type hints if needed
import constants
import os
from typing import List, Callable, Any, Optional, Dict
import queue
import traceback
import threading # Import threading here as well

# Type for ViewModel listeners
ViewModelListener = Callable[[Dict[str, Any]], None]

class VideoViewModel:
    """
    ViewModel connecting the View (GUI) and the Model (VideoService).
    Handles application logic, state, and communication via a queue.
    """
    def __init__(self):
        """Initializes ViewModel."""
        self.message_queue = queue.Queue() # Thread-safe queue for View updates
        self.listeners: List[ViewModelListener] = []
        self.service = VideoService(self._log_message_to_queue) # Pass logger method
        self._current_context: Optional[ProcessingContext] = None # Store context if needed

    def add_listener(self, listener: ViewModelListener):
        """Adds a listener (typically the View) for updates."""
        if listener not in self.listeners:
            self.listeners.append(listener)

    def remove_listener(self, listener: ViewModelListener):
        """Removes a listener."""
        try:
            self.listeners.remove(listener)
        except ValueError:
            pass # Ignore if listener not found

    def _notify_listeners(self, message: Dict[str, Any]):
        """Notifies all listeners about an event (e.g., queue update)."""
        # This might be called from the worker thread.
        # Listeners (GUI) should handle thread safety (e.g., using root.after).
        for listener in self.listeners:
            try:
                listener(message)
            except Exception as e:
                # Log listener errors directly to console to avoid loops
                print(f"ERROR in ViewModel listener: {e}", flush=True)
                print(traceback.format_exc(), flush=True)

    def _log_message_to_queue(self, msg: str):
        """
        Logs a message by putting it into the thread-safe queue for the GUI.
        This method is passed to VideoService and Commands.
        """
        # Determine log level based on prefix (simple approach)
        level = "INFO" # Default
        if msg.startswith("[ERROR]"):
             level = "ERROR"
        elif msg.startswith("[WARN]"):
             level = "WARN"
        elif msg.startswith("▶") or msg.startswith("✔") or msg.startswith("🎉"):
             level = "INFO" # Or a custom "PROGRESS" level
        elif msg.startswith("✖") or msg.startswith("❌"):
             level = "ERROR"
        elif msg.startswith("[DEBUG]"): # Allow debug messages if needed
             level = "DEBUG"
             # Optional: Don't show debug messages in GUI unless a flag is set
             # return

        log_event = {"type": "log", "level": level, "data": msg}
        self.message_queue.put(log_event)
        # Notify listeners that the queue has new data
        self._notify_listeners({"type": "queue_update"})


    def run(self, url: str, yandex_audio: Optional[str], actions: List[str], output_dir: str):
        """
        Starts the video processing tasks in a separate thread.

        Args:
            url: Video URL.
            yandex_audio: Path to Yandex audio file (optional).
            actions: List of action keys.
            output_dir: Directory for output files.
        """
        # Signal start to GUI via queue
        self.message_queue.put({"type": "status", "level":"INFO", "data": "running"})
        self._notify_listeners({"type": "queue_update"})

        # Define the target function for the thread
        def task():
            success = False
            try:
                # Run the service logic
                success = self.service.perform_actions(url, yandex_audio, actions, output_dir)
            except Exception as e:
                # Catch unexpected errors from the service layer itself
                error_msg = f"Critical error in VideoService execution: {type(e).__name__} - {e}"
                self._log_message_to_queue(f"[ERROR] {error_msg}")
                self._log_message_to_queue(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
                success = False
            finally:
                # Signal end to GUI via queue
                status = "finished" if success else "error"
                level = "INFO" if success else "ERROR"
                self.message_queue.put({"type": "status", "level": level, "data": status})
                self._notify_listeners({"type": "queue_update"})

        # Create and start the worker thread
        thread = threading.Thread(target=task, daemon=True)
        thread.start()


    def get_message_from_queue(self) -> Optional[Dict[str, Any]]:
        """
        Retrieves one message from the queue (non-blocking).
        Intended for use by the View in its main loop.

        Returns:
            A message dictionary or None if the queue is empty.
        """
        try:
            return self.message_queue.get_nowait()
        except queue.Empty:
            return None