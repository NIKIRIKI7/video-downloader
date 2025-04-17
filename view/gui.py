import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import queue
import os

from viewmodel.video_viewmodel import VideoViewModel
import constants # For default dir and poll interval
from utils.utils import find_executable
from typing import Dict, Any, Optional

class VideoAppGUI:
    """
    GUI for the Video Processing Application using MVVM pattern.
    """

    def __init__(self, root: tk.Tk, view_model: VideoViewModel):
        """Initialize the GUI."""
        self.root = root
        self.vm = view_model
        self.vm.add_listener(self._handle_vm_notification)

        self.root.title("Video Processing App (MVVM)")
        self.root.geometry("750x600") # Increased size for output dir

        # --- Style ---
        style = ttk.Style()
        style.theme_use('clam') # Or 'alt', 'default', 'classic'

        # --- Main Frame ---
        frm = ttk.Frame(self.root, padding=15)
        frm.pack(fill=tk.BOTH, expand=True)

        # --- Input Fields ---
        input_frame = ttk.Frame(frm)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        input_frame.columnconfigure(1, weight=1)

        # Video URL
        ttk.Label(input_frame, text="Video URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.url_ent = ttk.Entry(input_frame, width=60)
        self.url_ent.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3)

        # Yandex Audio
        ttk.Label(input_frame, text="Yandex Audio (MP3):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.y_ent = ttk.Entry(input_frame, width=50)
        self.y_ent.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=3)
        self.browse_y_btn = ttk.Button(input_frame, text="Browse...", command=self._browse_yandex_audio)
        self.browse_y_btn.grid(row=1, column=2, padx=(5, 0), pady=3)

        # Output Directory
        ttk.Label(input_frame, text="Output Directory:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.out_dir_var = tk.StringVar(value=constants.VIDEO_DIR_DEFAULT) # Default value
        self.out_dir_ent = ttk.Entry(input_frame, textvariable=self.out_dir_var, width=50)
        self.out_dir_ent.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=3)
        self.browse_out_btn = ttk.Button(input_frame, text="Browse...", command=self._browse_output_dir)
        self.browse_out_btn.grid(row=2, column=2, padx=(5, 0), pady=3)


        # --- Actions ---
        actions_frame = ttk.LabelFrame(frm, text=" Actions ", padding=10)
        actions_frame.pack(fill=tk.X, pady=5)
        self.action_vars: Dict[str, tk.BooleanVar] = {}
        self.action_cbs: Dict[str, ttk.Checkbutton] = {} # Store Checkbuttons too
        action_definitions = [
            ('md', '1. Download Metadata (ID, Title, Desc)'),
            ('dv', '2. Download Video (MP4)'),
            ('ds', '3. Download Subtitles (EN, VTT)'),
            ('dt', '4. Translate Subtitles (RU, VTT)'),
            ('da', '5. Mix Audio (with Yandex Audio)')
            # ('tm', '6. Translate Metadata (RU)'), # Add if needed
        ]
        cols = 2 # Arrange in 2 columns
        for i, (key, label) in enumerate(action_definitions):
            var = tk.BooleanVar()
            cb = ttk.Checkbutton(actions_frame, text=label, variable=var)
            cb.grid(row=i // cols, column=i % cols, padx=10, pady=3, sticky=tk.W)
            self.action_vars[key] = var
            self.action_cbs[key] = cb # Store reference
        actions_frame.columnconfigure(0, weight=1)
        actions_frame.columnconfigure(1, weight=1)


        # --- Log Area ---
        log_frame = ttk.LabelFrame(frm, text=" Execution Log ", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_txt = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, state=tk.DISABLED)
        self.log_txt.pack(fill=tk.BOTH, expand=True)
        # Configure tags for log levels
        self.log_txt.tag_configure("INFO", foreground="black")
        self.log_txt.tag_configure("WARN", foreground="orange")
        self.log_txt.tag_configure("ERROR", foreground="red")
        self.log_txt.tag_configure("DEBUG", foreground="grey")


        # --- Progress & Control ---
        progress_control_frame = ttk.Frame(frm)
        progress_control_frame.pack(fill=tk.X, pady=(5, 0))
        progress_control_frame.columnconfigure(0, weight=1)

        self.progress = ttk.Progressbar(progress_control_frame, mode='indeterminate')
        self.progress.grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.EW)

        self.start_btn = ttk.Button(progress_control_frame, text="Start Processing", command=self._on_start)
        self.start_btn.grid(row=1, column=0, padx=5, pady=(10, 0))

        # Simple clear log button
        self.clear_log_btn = ttk.Button(progress_control_frame, text="Clear Log", command=self._clear_log)
        self.clear_log_btn.grid(row=1, column=1, padx=5, pady=(10, 0))


        # --- State ---
        self._is_running = False

        # --- Initial Checks ---
        self._check_external_tools()

        # Start checking the ViewModel's queue
        self.root.after(constants.QUEUE_POLL_INTERVAL_MS, self._check_vm_queue_periodically)

    def _check_external_tools(self):
        """Check for yt-dlp and ffmpeg on startup."""
        missing = []
        try:
            if not find_executable('yt-dlp', constants.YTDLP_PATH):
                missing.append('yt-dlp')
        except Exception: # Catch potential errors during check
            missing.append('yt-dlp (check failed)')

        try:
            if not find_executable('ffmpeg', constants.FFMPEG_PATH):
                missing.append('ffmpeg')
        except Exception:
             missing.append('ffmpeg (check failed)')


        if missing:
             messagebox.showwarning(
                 "Missing Tools",
                 f"The following required tools were not found:\n\n"
                 f"- {', '.join(missing)}\n\n"
                 f"Please ensure they are installed and accessible via your system's PATH, "
                 f"or specify their full paths in constants.py.\n\n"
                 f"Some actions may fail."
             )

    def _browse_yandex_audio(self):
        """Opens dialog to select the Yandex MP3 file."""
        filename = filedialog.askopenfilename(
            title="Select Yandex Audio MP3 File",
            filetypes=[("MP3 audio", "*.mp3"), ("All files", "*.*")]
        )
        if filename:
            self.y_ent.delete(0, tk.END)
            self.y_ent.insert(0, filename)

    def _browse_output_dir(self):
        """Opens dialog to select the output directory."""
        dirname = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=self.out_dir_var.get() # Start from current value
        )
        if dirname:
            self.out_dir_var.set(dirname)

    def _set_controls_state(self, enabled: bool):
        """Enables or disables input controls and action checkboxes."""
        state = tk.NORMAL if enabled else tk.DISABLED
        widget_state = 'normal' if enabled else 'disabled' # For ttk widgets

        self.url_ent.config(state=widget_state)
        self.y_ent.config(state=widget_state)
        self.out_dir_ent.config(state=widget_state)
        self.browse_y_btn.config(state=widget_state)
        self.browse_out_btn.config(state=widget_state)
        self.start_btn.config(state=widget_state)
        # Also disable clear log button while running? Maybe not necessary.
        # self.clear_log_btn.config(state=widget_state)

        for cb in self.action_cbs.values():
            cb.config(state=widget_state)

    def _add_log_message(self, message: str, level: str = "INFO"):
        """Adds a message to the log area with appropriate tag."""
        self.log_txt.config(state=tk.NORMAL) # Enable writing
        # Use appropriate tag, default to INFO if level unknown
        tag = level if level in ["INFO", "WARN", "ERROR", "DEBUG"] else "INFO"
        self.log_txt.insert(tk.END, message + "\n", tag)
        self.log_txt.see(tk.END) # Auto-scroll
        self.log_txt.config(state=tk.DISABLED) # Disable writing

    def _clear_log(self):
        """Clears the log text area."""
        self.log_txt.config(state=tk.NORMAL)
        self.log_txt.delete('1.0', tk.END)
        self.log_txt.config(state=tk.DISABLED)

    def _on_start(self):
        """Handles the 'Start Processing' button click."""
        if self._is_running:
            return # Prevent multiple runs

        url = self.url_ent.get().strip()
        yandex_audio_path = self.y_ent.get().strip()
        output_dir = self.out_dir_var.get().strip()
        selected_actions = [key for key, var in self.action_vars.items() if var.get()]

        # --- Input Validation ---
        errors = []
        if not url:
            errors.append("Video URL is required.")
        if not selected_actions:
            errors.append("At least one action must be selected.")
        if not output_dir:
             errors.append("Output directory is required.")
        elif not os.path.isdir(output_dir):
             try:
                 # Try to create the directory if it doesn't exist
                 os.makedirs(output_dir, exist_ok=True)
                 self._add_log_message(f"[INFO] Created output directory: {output_dir}", "INFO")
             except OSError as e:
                 errors.append(f"Cannot create output directory: {e}")

        if 'da' in selected_actions:
            if not yandex_audio_path:
                errors.append("Yandex Audio file is required for 'Mix Audio' action.")
            elif not os.path.exists(yandex_audio_path):
                 errors.append(f"Yandex Audio file not found: {yandex_audio_path}")
            elif not yandex_audio_path.lower().endswith(".mp3"):
                 # Show warning but don't block unless it's critical
                 messagebox.showwarning("Warning", "Yandex Audio file does not end with .mp3. Ensure it's a valid audio file.")


        if errors:
            messagebox.showerror("Input Error", "\n".join(errors))
            return
        # --- End Validation ---

        # --- Start Processing ---
        self._is_running = True
        self._set_controls_state(enabled=False)
        self.progress.start(10) # Start indeterminate progress bar
        self._add_log_message("=" * 50, "INFO")
        self._add_log_message(">>> Starting processing...", "INFO")

        # Call ViewModel's run method (which starts a thread)
        self.vm.run(url, yandex_audio_path, selected_actions, output_dir)

    def _handle_vm_notification(self, message: Dict[str, Any]):
        """
        Handles notifications from the ViewModel.
        This is called by the ViewModel (potentially from a worker thread).
        It schedules the queue check in the main Tkinter thread.
        """
        if message.get("type") == "queue_update":
            # Schedule _process_vm_queue to run ASAP in the main thread
            self.root.after(0, self._process_vm_queue)

    def _process_vm_queue(self):
        """
        Processes all messages currently in the ViewModel's queue.
        This method runs in the main Tkinter thread.
        """
        if not hasattr(self, 'root') or not self.root.winfo_exists():
             return # Window closed

        try:
            while True: # Process all messages in the queue now
                message = self.vm.get_message_from_queue()
                if message is None:
                    break # Queue is empty

                msg_type = message.get("type")
                msg_data = message.get("data")
                msg_level = message.get("level", "INFO") # Get level, default INFO

                if msg_type == "log":
                    self._add_log_message(str(msg_data), msg_level)
                elif msg_type == "status":
                    if msg_data == "running":
                        # Already handled in _on_start, but could add specific UI changes here
                        pass
                    elif msg_data == "finished" or msg_data == "error":
                        # Processing finished (successfully or not)
                        self.progress.stop()
                        self._set_controls_state(enabled=True) # Re-enable controls
                        self._is_running = False

                        result_message = "✅ Processing finished successfully." if msg_data == "finished" else "❌ Processing finished with errors."
                        self._add_log_message(f">>> {result_message}", msg_level)
                        self._add_log_message("=" * 50, "INFO")

                        if msg_data == "error":
                            messagebox.showerror("Processing Error", "An error occurred during processing. Check the log for details.")
                        else:
                            messagebox.showinfo("Processing Complete", "Video processing tasks finished successfully.")

        except Exception as e:
            # Log errors during queue processing itself (should not happen often)
            print(f"ERROR processing ViewModel queue: {e}", flush=True)
            import traceback
            print(traceback.format_exc(), flush=True)
            # Attempt to add error to log if possible
            try:
                 self._add_log_message(f"[ERROR] Internal GUI Error processing queue: {e}", "ERROR")
            except:
                 pass # Avoid infinite loops

    def _check_vm_queue_periodically(self):
        """Periodically checks the VM queue by calling _process_vm_queue."""
        if not hasattr(self, 'root') or not self.root.winfo_exists():
             return # Stop scheduling if window closed

        self._process_vm_queue() # Process any messages currently in the queue
        # Reschedule the next check
        self.root.after(constants.QUEUE_POLL_INTERVAL_MS, self._check_vm_queue_periodically)


# --- GUI Launch Function ---
def create_gui():
    """Creates the Tkinter root window, ViewModel, GUI, and runs the main loop."""
    root = tk.Tk()
    vm = VideoViewModel() # Create ViewModel instance
    app = VideoAppGUI(root, vm) # Create GUI instance, passing root and VM
    root.mainloop()