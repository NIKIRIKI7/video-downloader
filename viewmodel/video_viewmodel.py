from model.video_service import VideoService
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
    ViewModel connecting the View (GUI) and the Model (VideoService).
    Handles application logic orchestration, state management (like is_running,
    though GUI handles its own _is_running), and communication between View and Model
    via a thread-safe queue.
    """
    def __init__(self):
        """Initializes ViewModel, message queue, and VideoService."""
        # Thread-safe queue for sending messages (logs, status) from Model/VM to View
        self.message_queue = queue.Queue()
        # List of listeners (usually just the GUI) to notify about queue updates
        self.listeners: List[ViewModelListener] = []
        # Instantiate the VideoService, passing the method to log messages back to the queue
        self.service = VideoService(self._log_message_to_queue)
        # Internal state tracking if needed (e.g., to prevent multiple runs from VM side)
        self._is_processing = False
        self._processing_thread: Optional[threading.Thread] = None

    def add_listener(self, listener: ViewModelListener):
        """Adds a listener function (e.g., GUI's _handle_vm_notification)."""
        if listener not in self.listeners:
            self.listeners.append(listener)

    def remove_listener(self, listener: ViewModelListener):
        """Removes a listener function."""
        try:
            self.listeners.remove(listener)
        except ValueError:
            pass # Ignore if listener was already removed or not found

    def _notify_listeners(self, message: Dict[str, Any]):
        """
        Notifies all registered listeners about an event.
        This might be called from the worker thread, so listeners (GUI)
        must handle thread safety (e.g., using `root.after` in Tkinter).
        The message typically indicates that there's new data in the queue.
        """
        for listener in self.listeners:
            try:
                # Call the listener function with the message
                listener(message)
            except Exception as e:
                # Log errors in listener execution directly to console to avoid loops/crashes
                print(f"ERROR executing ViewModel listener {listener.__name__}: {e}", flush=True)
                print(traceback.format_exc(), flush=True)

    def _log_message_to_queue(self, msg: str):
        """
        Logs a message originating from the Model (VideoService, Commands)
        by putting it into the thread-safe queue for the View to process.
        Also determines a basic log level based on message prefixes.
        """
        # Determine log level based on simple prefix matching (case-insensitive)
        level = "INFO" # Default level
        msg_lower = msg.lower()
        if msg_lower.startswith("[error]") or msg_lower.startswith("✖") or msg_lower.startswith("❌"):
             level = "ERROR"
        elif msg_lower.startswith("[warn]"):
             level = "WARN"
        elif msg_lower.startswith("▶") or msg_lower.startswith("✔") or msg_lower.startswith("🎉") or msg_lower.startswith("✅"):
             # Consider a more specific level like "PROGRESS" or "SUCCESS" if needed by View
             level = "INFO" # Treat these progress/success markers as INFO for now
        elif msg_lower.startswith("[debug]"):
             level = "DEBUG"
             # Optional: Filter out debug messages unless a global debug flag is set
             # if not DEBUG_MODE: return

        # Create the message dictionary
        log_event = {"type": "log", "level": level, "data": msg}
        # Put the message onto the queue
        self.message_queue.put(log_event)
        # Notify listeners that the queue has been updated
        # Pass a simple notification message, the listener will pull from the queue
        self._notify_listeners({"type": "queue_update"})


    def run(self, url: str, yandex_audio: Optional[str], actions: List[str], output_dir: str, settings: Dict[str, Any]):
        """
        Starts the video processing task (VideoService.perform_actions)
        in a separate background thread.

        Args:
            url: Video URL.
            yandex_audio: Path to external audio file (optional).
            actions: List of action keys selected by the user.
            output_dir: Directory for output files.
            settings: Dictionary of settings collected from the GUI.
        """
        # Prevent starting a new process if one is already running
        if self._is_processing and self._processing_thread and self._processing_thread.is_alive():
             self._log_message_to_queue("[WARN] Another processing task is already running.")
             # Optionally notify listeners immediately about this warning
             # self._notify_listeners({"type":"status", "data":"already_running"})
             return

        self._is_processing = True # Set processing flag

        # Signal start to GUI via queue immediately before starting thread
        self.message_queue.put({"type": "status", "level":"INFO", "data": "running"})
        self._notify_listeners({"type": "queue_update"})

        # Define the target function for the background thread
        def task():
            success = False # Track success of the operation
            try:
                # Call the core logic in VideoService, passing all necessary data
                success = self.service.perform_actions(url, yandex_audio, actions, output_dir, settings)
            except Exception as e:
                # Catch unexpected errors that might occur *within* the service layer itself
                # (Errors within commands should ideally be caught and logged by the service loop)
                error_msg = f"Critical error during VideoService execution: {type(e).__name__} - {e}"
                self._log_message_to_queue(f"[ERROR] {error_msg}")
                # Log the full traceback for debugging critical errors
                self._log_message_to_queue(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
                success = False # Ensure status reflects the critical error
            finally:
                # This block executes whether the try block succeeded or raised an exception
                # Signal completion status (finished or error) to GUI via queue
                status = "finished" if success else "error"
                level = "INFO" if success else "ERROR"
                self.message_queue.put({"type": "status", "level": level, "data": status})
                self._notify_listeners({"type": "queue_update"})
                # Reset processing flag when task finishes
                self._is_processing = False

        # Create and start the background thread
        # Mark as daemon so it exits if the main program exits unexpectedly
        self._processing_thread = threading.Thread(target=task, daemon=True)
        self._processing_thread.start()


    def get_message_from_queue(self) -> Optional[Dict[str, Any]]:
        """
        Allows the View (or other listeners) to retrieve one message
        from the queue in a non-blocking way.

        Returns:
            A message dictionary if one is available, otherwise None.
        """
        try:
            # Get message without waiting
            return self.message_queue.get_nowait()
        except queue.Empty:
            # Return None if the queue is currently empty
            return None