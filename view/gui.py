import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
import queue
import os
import re # For validation if needed
import traceback # For detailed error logging

from viewmodel.video_viewmodel import VideoViewModel
import constants # For default values and poll interval
from utils.utils import find_executable # For initial tool check
from typing import Dict, Any, Optional, List # Added List

class VideoAppGUI:
    """
    GUI for the Video Processing Application using MVVM pattern.
    Includes settings tab for configurable parameters.
    """

    def __init__(self, root: tk.Tk, view_model: VideoViewModel):
        """Initialize the GUI."""
        self.root = root
        self.vm = view_model
        self.vm.add_listener(self._handle_vm_notification)

        self.root.title("Video Processing App") # Shorter title
        self.root.geometry("800x700") # Adjusted size for settings tab

        # --- Style ---
        style = ttk.Style()
        # Use a theme that works well across platforms if possible
        try:
            # 'clam', 'alt', 'default', 'classic' are common tk themes
            # 'vista', 'xpnative', 'winative' on Windows
            # 'aqua' on macOS
            style.theme_use('clam') # 'clam' is often a good cross-platform choice
        except tk.TclError:
            print("Warning: 'clam' theme not found, using default theme.")
            # Fallback to default if 'clam' is not available

        # --- Main Structure: Notebook for Tabs ---
        main_notebook = ttk.Notebook(self.root)
        main_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- Tab 1: Main Processing ---
        process_tab = ttk.Frame(main_notebook, padding=10)
        main_notebook.add(process_tab, text='Process Video')

        # --- Input Fields ---
        input_frame = ttk.LabelFrame(process_tab, text="Inputs", padding=10)
        input_frame.pack(fill=tk.X, pady=(0, 10))
        input_frame.columnconfigure(1, weight=1) # Allow entry field to expand

        ttk.Label(input_frame, text="Video URL:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.url_ent = ttk.Entry(input_frame, width=60)
        self.url_ent.grid(row=0, column=1, sticky=tk.EW, padx=5, pady=3)

        ttk.Label(input_frame, text="Yandex Audio File:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.y_ent = ttk.Entry(input_frame, width=50)
        self.y_ent.grid(row=1, column=1, sticky=tk.EW, padx=5, pady=3)
        self.browse_y_btn = ttk.Button(input_frame, text="Browse...", command=self._browse_yandex_audio)
        self.browse_y_btn.grid(row=1, column=2, padx=(5, 0), pady=3)

        ttk.Label(input_frame, text="Output Directory:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.out_dir_var = tk.StringVar(value=constants.VIDEO_DIR_DEFAULT) # Default value from constants
        self.out_dir_ent = ttk.Entry(input_frame, textvariable=self.out_dir_var, width=50)
        self.out_dir_ent.grid(row=2, column=1, sticky=tk.EW, padx=5, pady=3)
        self.browse_out_btn = ttk.Button(input_frame, text="Browse...", command=self._browse_output_dir)
        self.browse_out_btn.grid(row=2, column=2, padx=(5, 0), pady=3)

        # --- Actions ---
        actions_frame = ttk.LabelFrame(process_tab, text="Actions", padding=10)
        actions_frame.pack(fill=tk.X, pady=5)
        self.action_vars: Dict[str, tk.BooleanVar] = {}
        self.action_cbs: Dict[str, ttk.Checkbutton] = {} # Store Checkbuttons too
        # Use the mapping from VideoService for consistency if possible, or define here
        action_definitions = [
            ('md', '1. Download Metadata (ID, Title, Desc)'),
            ('dv', '2. Download Video'),
            ('ds', '3. Download Subtitles'),
            ('dt', '4. Translate Subtitles'),
            ('da', '5. Mix Audio (with Yandex Audio)'),
            ('tm', '6. Translate Metadata'), # Add if TranslateMetadata command is used
        ]
        cols = 2 # Arrange actions in 2 columns
        for i, (key, label) in enumerate(action_definitions):
            var = tk.BooleanVar()
            # Optional: Set default checked state for common actions
            # if key in ['md', 'dv', 'ds', 'da']: var.set(True)
            cb = ttk.Checkbutton(actions_frame, text=label, variable=var)
            cb.grid(row=i // cols, column=i % cols, padx=10, pady=3, sticky=tk.W)
            self.action_vars[key] = var
            self.action_cbs[key] = cb # Store reference for enabling/disabling
        actions_frame.columnconfigure(0, weight=1) # Give columns equal weight
        actions_frame.columnconfigure(1, weight=1)

        # --- Log Area ---
        log_frame = ttk.LabelFrame(process_tab, text="Execution Log", padding=5)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        self.log_txt = scrolledtext.ScrolledText(log_frame, height=15, wrap=tk.WORD, state=tk.DISABLED, font=("Consolas", 9) if os.name == 'nt' else ("Monaco", 10) if os.name == 'posix' else ("Courier", 10)) # Monospaced font preference
        self.log_txt.pack(fill=tk.BOTH, expand=True)
        # Configure tags for log levels - use distinct colors
        self.log_txt.tag_configure("INFO", foreground="black")
        self.log_txt.tag_configure("WARN", foreground="#E69900") # Dark Orange
        self.log_txt.tag_configure("ERROR", foreground="red")
        self.log_txt.tag_configure("DEBUG", foreground="grey")
        self.log_txt.tag_configure("SUCCESS", foreground="green") # For success indicators like 'Finished'

        # --- Progress & Control ---
        progress_control_frame = ttk.Frame(process_tab)
        progress_control_frame.pack(fill=tk.X, pady=(5, 0))
        progress_control_frame.columnconfigure(0, weight=1) # Make progress bar expand

        self.progress = ttk.Progressbar(progress_control_frame, mode='indeterminate')
        # Span across two columns if buttons are side-by-side
        self.progress.grid(row=0, column=0, columnspan=2, pady=5, sticky=tk.EW)

        self.start_btn = ttk.Button(progress_control_frame, text="Start Processing", command=self._on_start)
        self.start_btn.grid(row=1, column=0, padx=5, pady=(10, 0), sticky=tk.E) # Align right

        self.clear_log_btn = ttk.Button(progress_control_frame, text="Clear Log", command=self._clear_log)
        self.clear_log_btn.grid(row=1, column=1, padx=5, pady=(10, 0), sticky=tk.W) # Align left
        # Give columns equal weight to center buttons approximately
        progress_control_frame.columnconfigure(0, weight=1)
        progress_control_frame.columnconfigure(1, weight=1)


        # --- Tab 2: Settings ---
        settings_tab = ttk.Frame(main_notebook, padding=15)
        main_notebook.add(settings_tab, text='Settings')

        # Use a single frame within the settings tab for structure
        settings_frame = ttk.Frame(settings_tab)
        settings_frame.pack(fill=tk.BOTH, expand=True) # Allow settings content to expand
        # Configure columns for label and entry fields
        settings_frame.columnconfigure(1, weight=1) # Allow entry fields to expand horizontally

        # Group settings logically using LabelFrames
        current_row = 0 # Keep track of grid row

        # -- Language & Subtitle Settings --
        lang_frame = ttk.LabelFrame(settings_frame, text="Languages & Subtitles", padding=10)
        lang_frame.grid(row=current_row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        lang_frame.columnconfigure(1, weight=0) # Don't let language entry fields expand too much
        current_row += 1

        ttk.Label(lang_frame, text="Source Language (Translate From):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.source_lang_var = tk.StringVar(value=constants.SOURCE_LANG_DEFAULT)
        self.source_lang_ent = ttk.Entry(lang_frame, textvariable=self.source_lang_var, width=10)
        self.source_lang_ent.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(lang_frame, text="Target Language (Translate To):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.target_lang_var = tk.StringVar(value=constants.TARGET_LANG_DEFAULT)
        self.target_lang_ent = ttk.Entry(lang_frame, textvariable=self.target_lang_var, width=10)
        self.target_lang_ent.grid(row=1, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(lang_frame, text="Subtitle Download Lang:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.subtitle_lang_var = tk.StringVar(value=constants.SUB_LANG_DEFAULT)
        self.subtitle_lang_ent = ttk.Entry(lang_frame, textvariable=self.subtitle_lang_var, width=10)
        self.subtitle_lang_ent.grid(row=2, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(lang_frame, text="Subtitle Format (e.g., vtt, srt):").grid(row=3, column=0, sticky=tk.W, padx=5, pady=3)
        self.subtitle_format_var = tk.StringVar(value=constants.SUB_FORMAT_DEFAULT)
        self.subtitle_format_ent = ttk.Entry(lang_frame, textvariable=self.subtitle_format_var, width=10)
        self.subtitle_format_ent.grid(row=3, column=1, sticky=tk.W, padx=5, pady=3)

        # -- Audio Mixing Settings --
        audio_frame = ttk.LabelFrame(settings_frame, text="Audio Mixing (FFmpeg)", padding=10)
        audio_frame.grid(row=current_row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        audio_frame.columnconfigure(1, weight=0) # Keep volume fields narrow
        current_row += 1

        ttk.Label(audio_frame, text="Original Video Volume (0.0=Mute, 1.0=Normal):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.original_volume_var = tk.StringVar(value=constants.ORIGINAL_VOLUME_DEFAULT)
        self.original_volume_ent = ttk.Entry(audio_frame, textvariable=self.original_volume_var, width=10)
        self.original_volume_ent.grid(row=0, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(audio_frame, text="Added (Yandex) Volume (1.0=Normal):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.added_volume_var = tk.StringVar(value=constants.ADDED_VOLUME_DEFAULT)
        self.added_volume_ent = ttk.Entry(audio_frame, textvariable=self.added_volume_var, width=10)
        self.added_volume_ent.grid(row=1, column=1, sticky=tk.W, padx=5, pady=3)

        ttk.Label(audio_frame, text="Merged Audio Codec (e.g., aac, mp3):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=3)
        self.merged_audio_codec_var = tk.StringVar(value=constants.MERGED_AUDIO_CODEC_DEFAULT)
        self.merged_audio_codec_ent = ttk.Entry(audio_frame, textvariable=self.merged_audio_codec_var, width=10)
        self.merged_audio_codec_ent.grid(row=2, column=1, sticky=tk.W, padx=5, pady=3)


        # -- Download Settings (yt-dlp) --
        dl_frame = ttk.LabelFrame(settings_frame, text="Download (yt-dlp)", padding=10)
        dl_frame.grid(row=current_row, column=0, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        dl_frame.columnconfigure(1, weight=1) # Allow format code field to expand
        current_row += 1

        # Add tooltip or help text for format code? Maybe later.
        ttk.Label(dl_frame, text="Video Format Code (see yt-dlp -F):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=3)
        self.yt_dlp_format_var = tk.StringVar(value=constants.YT_DLP_FORMAT_DEFAULT)
        self.yt_dlp_format_ent = ttk.Entry(dl_frame, textvariable=self.yt_dlp_format_var, width=50) # Wider field for complex codes
        self.yt_dlp_format_ent.grid(row=0, column=1, columnspan=2, sticky=tk.EW, padx=5, pady=3)

        ttk.Label(dl_frame, text="Output Video Container (e.g., mp4, mkv):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=3)
        self.video_format_ext_var = tk.StringVar(value=constants.VIDEO_FORMAT_EXT_DEFAULT)
        self.video_format_ext_ent = ttk.Entry(dl_frame, textvariable=self.video_format_ext_var, width=10)
        self.video_format_ext_ent.grid(row=1, column=1, sticky=tk.W, padx=5, pady=3)

        # --- Placeholder for potential future settings ---
        # settings_frame.rowconfigure(current_row, weight=1) # Allow empty space at bottom

        # --- State ---
        self._is_running = False

        # --- Initial Checks ---
        self._check_external_tools() # Check tools on startup

        # Start checking the ViewModel's queue periodically
        self.root.after(constants.QUEUE_POLL_INTERVAL_MS, self._check_vm_queue_periodically)


    def _check_external_tools(self):
        """Check for yt-dlp and ffmpeg on startup and show a warning if missing."""
        missing = []
        # Use constants for configured paths
        ytdlp_path_const = constants.YTDLP_PATH
        ffmpeg_path_const = constants.FFMPEG_PATH

        # Check yt-dlp
        try:
            if not find_executable('yt-dlp', ytdlp_path_const):
                missing.append('yt-dlp')
        except Exception as e:
            print(f"Error checking for yt-dlp: {e}")
            missing.append('yt-dlp (check failed)')

        # Check ffmpeg
        try:
            if not find_executable('ffmpeg', ffmpeg_path_const):
                missing.append('ffmpeg')
        except Exception as e:
            print(f"Error checking for ffmpeg: {e}")
            missing.append('ffmpeg (check failed)')

        if missing:
             # Use messagebox for immediate user feedback
             messagebox.showwarning(
                 "Missing External Tools",
                 f"Could not find the following required tool(s):\n\n"
                 f"- {', '.join(missing)}\n\n"
                 f"Please ensure they are installed and accessible via your system's PATH environment variable, "
                 f"or specify their full paths in the 'constants.py' file.\n\n"
                 f"Actions requiring these tools may fail."
             )
             # Also log to console/log area
             self._add_log_message(f"[WARN] Missing required tools: {', '.join(missing)}. Check installation/PATH/constants.py.", "WARN")


    def _browse_yandex_audio(self):
        """Opens dialog to select the Yandex (or other external) audio file."""
        filename = filedialog.askopenfilename(
            title="Select External Audio File",
            # Provide common audio file types
            filetypes=[("Audio Files", "*.mp3 *.m4a *.aac *.wav *.ogg"), ("All files", "*.*")]
        )
        if filename:
            self.y_ent.delete(0, tk.END)
            self.y_ent.insert(0, filename)


    def _browse_output_dir(self):
        """Opens dialog to select the output directory."""
        # Start browsing from the currently entered directory if it exists
        initial_dir = self.out_dir_var.get()
        if not os.path.isdir(initial_dir):
             initial_dir = constants.VIDEO_DIR_DEFAULT # Fallback to default

        dirname = filedialog.askdirectory(
            title="Select Output Directory",
            initialdir=initial_dir,
            mustexist=False # Allow creating a new directory from the dialog (on some platforms)
        )
        if dirname:
            self.out_dir_var.set(dirname)


    def _get_all_gui_widgets(self) -> List[tk.Widget]:
        """Helper to gather all relevant input widgets for state changes."""
        widgets = [
            # Main Tab Inputs
            self.url_ent, self.y_ent, self.out_dir_ent,
            self.browse_y_btn, self.browse_out_btn,
            self.start_btn,
            # Clear log button can remain enabled: self.clear_log_btn,
            # Settings Tab Inputs
            self.source_lang_ent, self.target_lang_ent, self.subtitle_lang_ent,
            self.subtitle_format_ent, self.original_volume_ent, self.added_volume_ent,
            self.merged_audio_codec_ent, self.yt_dlp_format_ent, self.video_format_ext_ent
        ]
        # Add all action checkboxes
        widgets.extend(self.action_cbs.values())
        # Filter out None just in case some widget wasn't created
        return [widget for widget in widgets if widget is not None]


    def _set_controls_state(self, enabled: bool):
        """Enables or disables input controls, action checkboxes, and settings fields."""
        state = tk.NORMAL if enabled else tk.DISABLED
        # ttk widgets use 'state' parameter: 'normal' or 'disabled'
        widget_state = 'normal' if enabled else 'disabled'

        for widget in self._get_all_gui_widgets():
            try:
                 # Check the type and apply the correct state setting method
                 if isinstance(widget, (ttk.Entry, ttk.Button, ttk.Checkbutton)):
                     widget.configure(state=widget_state)
                 elif isinstance(widget, tk.Entry): # Should not happen if using ttk consistently
                      widget.config(state=state)
                 # Add other widget types if used (e.g., tk.Spinbox)
            except tk.TclError as e:
                 # Ignore errors if a widget is already destroyed (e.g., during shutdown)
                 # print(f"Warning: TclError setting state for {widget}: {e}")
                 pass
            except Exception as e:
                 # Catch other potential errors during state setting
                 print(f"Error setting state for widget {widget}: {e}")


    def _add_log_message(self, message: str, level: str = "INFO"):
        """Adds a message to the scrolled text log area with appropriate tag/color."""
        # Ensure GUI elements exist before trying to update
        if not hasattr(self, 'log_txt') or not self.log_txt.winfo_exists():
            print(f"LOG ({level}): {message}") # Fallback to console output
            return

        try:
            # Make widget writable
            self.log_txt.config(state=tk.NORMAL)
            # Determine the tag based on level (case-insensitive)
            tag = level.upper() if level.upper() in ["INFO", "WARN", "ERROR", "DEBUG", "SUCCESS"] else "INFO"
            # Insert message and newline, applying the tag
            self.log_txt.insert(tk.END, message + "\n", tag)
            # Auto-scroll to the end
            self.log_txt.see(tk.END)
            # Make widget read-only again
            self.log_txt.config(state=tk.DISABLED)
            # Force GUI update to show the message immediately, especially useful
            # if called from the main thread during setup or validation.
            # Be cautious using this excessively within the periodic queue check.
            # self.root.update_idletasks()
        except Exception as e:
            # Log errors related to updating the GUI log itself to the console
            print(f"CRITICAL: Error adding message to GUI log: {e}", flush=True)
            print(f"Original message ({level}): {message}", flush=True)


    def _clear_log(self):
        """Clears the log text area."""
        if not hasattr(self, 'log_txt') or not self.log_txt.winfo_exists():
            return # Avoid error if called after window closed
        try:
            self.log_txt.config(state=tk.NORMAL)
            self.log_txt.delete('1.0', tk.END)
            self.log_txt.config(state=tk.DISABLED)
        except Exception as e:
             print(f"Error clearing GUI log: {e}")


    def _validate_settings(self, settings: Dict[str, Any]) -> List[str]:
        """Performs basic validation on the collected settings dictionary."""
        errors = []
        # --- Volume Validation ---
        try:
            vol_orig = float(settings['original_volume'])
            if vol_orig < 0: errors.append("Original Volume cannot be negative.")
        except ValueError:
            errors.append("Original Volume must be a number (e.g., 0.0, 0.5, 1.0).")
        try:
            vol_added = float(settings['added_volume'])
            if vol_added < 0: errors.append("Added Volume cannot be negative.")
        except ValueError:
            errors.append("Added Volume must be a number (e.g., 1.0, 1.5).")

        # --- Language Code Validation (Basic) ---
        # Simple check for non-empty, 2-3 letters (common convention)
        lang_pattern = re.compile(r"^[a-zA-Z]{2,3}(-[a-zA-Z]{2,4})?$") # e.g., en, es, pt-br
        if not settings['source_lang']: errors.append("Source Language cannot be empty.")
        # elif not lang_pattern.match(settings['source_lang']): errors.append("Source Language format seems incorrect (e.g., 'en', 'es').")
        if not settings['target_lang']: errors.append("Target Language cannot be empty.")
        # elif not lang_pattern.match(settings['target_lang']): errors.append("Target Language format seems incorrect (e.g., 'ru', 'pt-br').")
        if not settings['subtitle_lang']: errors.append("Subtitle Download Lang cannot be empty.")
        # elif not lang_pattern.match(settings['subtitle_lang']): errors.append("Subtitle Download Lang format seems incorrect.")

        # --- Format/Codec Validation (Basic non-empty check) ---
        if not settings['subtitle_format'].strip(): errors.append("Subtitle Format cannot be empty.")
        if not settings['yt_dlp_format'].strip(): errors.append("Video Format Code (yt-dlp) cannot be empty.")
        if not settings['video_format_ext'].strip(): errors.append("Output Video Container extension cannot be empty.")
        if not settings['merged_audio_codec'].strip(): errors.append("Merged Audio Codec cannot be empty.")

        # --- Extension/Format Sanitization ---
        # Remove leading dots from extensions if user added them
        settings['video_format_ext'] = settings['video_format_ext'].lstrip('.')
        settings['subtitle_format'] = settings['subtitle_format'].lstrip('.')

        return errors


    def _on_start(self):
        """Handles the 'Start Processing' button click: collects inputs, validates, starts VM task."""
        if self._is_running:
            self._add_log_message("[WARN] Processing is already running.", "WARN")
            return # Prevent multiple concurrent runs

        # --- 1. Collect Inputs from Main Tab ---
        url = self.url_ent.get().strip()
        yandex_audio_path = self.y_ent.get().strip()
        output_dir = self.out_dir_var.get().strip()
        selected_actions = [key for key, var in self.action_vars.items() if var.get()]

        # --- 2. Collect Settings from Settings Tab ---
        # Use .strip() and .lower() where appropriate (languages, formats, codecs)
        settings = {
            'source_lang': self.source_lang_var.get().strip().lower(),
            'target_lang': self.target_lang_var.get().strip().lower(),
            'subtitle_lang': self.subtitle_lang_var.get().strip().lower(),
            'subtitle_format': self.subtitle_format_var.get().strip().lower(),
            'original_volume': self.original_volume_var.get().strip(), # Keep as string for now
            'added_volume': self.added_volume_var.get().strip(),     # Keep as string for now
            'merged_audio_codec': self.merged_audio_codec_var.get().strip().lower(),
            'yt_dlp_format': self.yt_dlp_format_var.get().strip(), # Format code can be complex, keep case
            'video_format_ext': self.video_format_ext_var.get().strip().lower(), # Lowercase extension
        }

        # --- 3. Validate Inputs and Settings ---
        errors = []
        # Basic input validation
        if not url: errors.append("- Video URL is required.")
        if not selected_actions: errors.append("- At least one action must be selected.")
        if not output_dir:
             errors.append("- Output directory is required.")
        else:
            # Try to create output directory if it doesn't exist, BEFORE validation passes
            # This gives immediate feedback if creation fails.
            try:
                if not os.path.isdir(output_dir):
                    os.makedirs(output_dir, exist_ok=True)
                    self._add_log_message(f"[INFO] Created output directory: {output_dir}", "INFO")
            except OSError as e:
                errors.append(f"- Cannot create output directory: {e}")

        # Validate required Yandex audio only if 'da' (Mix Audio) action is selected
        if 'da' in selected_actions:
            if not yandex_audio_path:
                errors.append("- External Audio file is required for 'Mix Audio' action.")
            elif not os.path.exists(yandex_audio_path):
                 # Check existence again here, even if browsed earlier
                 errors.append(f"- External Audio file not found: {yandex_audio_path}")

        # Validate collected settings using the helper function
        setting_errors = self._validate_settings(settings)
        if setting_errors:
            errors.append("\nPlease check the Settings tab:")
            errors.extend([f"- {err}" for err in setting_errors])

        # --- 4. Show Errors or Start Processing ---
        if errors:
            error_message = "Please correct the following errors:\n\n" + "\n".join(errors)
            messagebox.showerror("Input Error", error_message)
            return # Stop execution if validation fails
        # --- End Validation ---

        # --- Start Processing ---
        self._is_running = True
        self._set_controls_state(enabled=False) # Disable controls
        self.progress.start(10) # Start indeterminate progress bar animation
        self._add_log_message("=" * 60, "INFO")
        self._add_log_message(">>> Starting processing with current settings...", "INFO")
        # Log key settings being used for this run
        self._add_log_message(f"[INFO] Actions: {selected_actions}", "INFO")
        self._add_log_message(f"[INFO] Output Dir: {output_dir}", "INFO")
        self._add_log_message(f"[INFO] Volume (Orig/Added): {settings['original_volume']}/{settings['added_volume']}", "INFO")
        self._add_log_message(f"[INFO] Languages (Down/Source/Target): {settings['subtitle_lang']}/{settings['source_lang']}/{settings['target_lang']}", "INFO")


        # Call ViewModel's run method, passing collected inputs and the validated settings dictionary
        try:
            self.vm.run(url, yandex_audio_path, selected_actions, output_dir, settings)
        except Exception as e:
             # Catch errors during the *initiation* of the VM task
             self._add_log_message(f"[ERROR] Failed to start processing thread: {e}", "ERROR")
             self._add_log_message(f"[DEBUG] Traceback:\n{traceback.format_exc()}", "DEBUG")
             messagebox.showerror("Error", f"Could not start processing: {e}")
             # Reset UI state if start failed
             self.progress.stop()
             self._set_controls_state(enabled=True)
             self._is_running = False


    # --- ViewModel Notification Handling ---

    def _handle_vm_notification(self, message: Dict[str, Any]):
        """
        Handles notifications from the ViewModel.
        This method is called by the ViewModel (potentially from a worker thread).
        It schedules the actual GUI update (_process_vm_queue) to run in the main Tkinter thread.
        """
        # Check if the root window still exists before scheduling
        if hasattr(self, 'root') and self.root.winfo_exists():
            # Schedule _process_vm_queue to run as soon as possible in the main event loop
            self.root.after(0, self._process_vm_queue)
        # else: print("GUI window closed, ignoring VM notification.")


    def _process_vm_queue(self):
        """
        Processes all messages currently in the ViewModel's queue.
        This method MUST run in the main Tkinter thread (scheduled by `root.after`).
        """
        # Extra safety check for root window existence
        if not hasattr(self, 'root') or not self.root.winfo_exists():
             return

        try:
            while True: # Process all messages currently in the queue
                message = self.vm.get_message_from_queue()
                if message is None:
                    break # Queue is empty for now

                # Process the message based on its type
                msg_type = message.get("type")
                msg_data = message.get("data")
                msg_level = message.get("level", "INFO") # Get level, default INFO

                if msg_type == "log":
                    self._add_log_message(str(msg_data), msg_level)
                elif msg_type == "status":
                    if msg_data == "running":
                        # This status is mainly handled by _on_start setting UI state.
                        # Could add specific UI changes here if needed upon actual thread start.
                        pass
                    elif msg_data == "finished" or msg_data == "error":
                        # Processing has ended (either successfully or with error)
                        self.progress.stop()
                        self._set_controls_state(enabled=True) # Re-enable all controls
                        self._is_running = False # Update state flag

                        is_success = (msg_data == "finished")
                        result_message = "✅ Processing finished successfully." if is_success else "❌ Processing finished with errors."
                        log_level = "SUCCESS" if is_success else "ERROR"

                        self._add_log_message(f">>> {result_message}", log_level)
                        self._add_log_message("=" * 60, "INFO") # Separator after finish

                        # Show final feedback message box
                        if is_success:
                            messagebox.showinfo("Processing Complete", "Selected tasks finished successfully.")
                        else:
                            messagebox.showerror("Processing Error", "An error occurred during processing. Please check the execution log for details.")
                # Handle other message types if needed in the future
                # elif msg_type == "progress_update":
                #    # Update a determinate progress bar
                #    pass

        except Exception as e:
            # Log errors that occur *during* queue processing itself (should be rare)
            print(f"CRITICAL ERROR processing ViewModel queue: {e}", flush=True)
            traceback.print_exc()
            # Attempt to add this internal error to the GUI log if possible
            try:
                 self._add_log_message(f"[ERROR] Internal GUI Error processing queue: {e}", "ERROR")
            except:
                 pass # Avoid infinite loops if logging itself fails


    def _check_vm_queue_periodically(self):
        """Periodically checks the VM queue by calling _process_vm_queue."""
        # Check if window is closed before processing or rescheduling
        if not hasattr(self, 'root') or not self.root.winfo_exists():
             # print("Stopping periodic queue check: window closed.")
             return # Stop scheduling if window is gone

        self._process_vm_queue() # Process any messages currently in the queue

        # Reschedule the next check using the interval from constants
        self.root.after(constants.QUEUE_POLL_INTERVAL_MS, self._check_vm_queue_periodically)


# --- GUI Launch Function ---
def create_gui():
    """Creates the Tkinter root window, ViewModel, GUI, and runs the main loop."""
    root = tk.Tk()
    vm = VideoViewModel() # Create ViewModel instance
    app = VideoAppGUI(root, vm) # Create GUI instance, passing root and VM
    # Set minimum size? Optional. root.minsize(750, 600)
    # Handle window closing? Optional. root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()