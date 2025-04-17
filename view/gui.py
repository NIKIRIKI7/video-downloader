import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
import threading
from viewmodel.video_viewmodel import VideoViewModel


def create_gui():
    vm = VideoViewModel()
    root = tk.Tk()
    root.title("Video App MVVM")
    root.geometry("600x500")
    frm = ttk.Frame(root, padding=10)
    frm.pack(fill=tk.BOTH, expand=True)

    # URL entry
    ttk.Label(frm, text="Video URL:").grid(row=0, column=0, sticky=tk.W)
    url_ent = ttk.Entry(frm)
    url_ent.grid(row=0, column=1, columnspan=3, sticky=tk.EW)
    frm.columnconfigure(1, weight=1)

    # Yandex audio
    ttk.Label(frm, text="Yandex Audio:").grid(row=1, column=0, sticky=tk.W)
    y_ent = ttk.Entry(frm)
    y_ent.grid(row=1, column=1, sticky=tk.EW)
    ttk.Button(frm, text="Browse", command=lambda: y_ent.insert(0, filedialog.askopenfilename(filetypes=[("MP3", "*.mp3")]))).grid(row=1, column=2)

    # Actions
    actions_frame = ttk.LabelFrame(frm, text="Actions")
    actions_frame.grid(row=2, column=0, columnspan=4, pady=10, sticky=tk.EW)
    action_vars = {}
    keys = [('dv', 'Download Video'), ('ds', 'Download Subs'), ('dt', 'Translate Subs'),
            ('md', 'Download Metadata'), ('da', 'Merge Audio')]
    for i, (key, label) in enumerate(keys):
        var = tk.BooleanVar()
        cb = ttk.Checkbutton(actions_frame, text=label, variable=var)
        cb.grid(row=i//3, column=i%3, padx=5, pady=2)
        action_vars[key] = var

    # Log
    log_txt = scrolledtext.ScrolledText(frm, height=15)
    log_txt.grid(row=3, column=0, columnspan=4, sticky=tk.NSEW)
    frm.rowconfigure(3, weight=1)

    # Progress
    progress = ttk.Progressbar(frm, mode='indeterminate')
    progress.grid(row=4, column=0, columnspan=4, sticky=tk.EW)

    # Bind ViewModel logs
    vm.add_listener(lambda msg: (log_txt.insert(tk.END, msg + "\n"), log_txt.see(tk.END)))

    def on_start():
        url = url_ent.get().strip()
        y = y_ent.get().strip()
        acts = [k for k, v in action_vars.items() if v.get()]
        if not url or not acts:
            messagebox.showerror("Error", "Specify URL and select actions.")
            return
        progress.start(10)
        threading.Thread(target=lambda: (vm.run(url, y, acts), progress.stop()), daemon=True).start()

    ttk.Button(frm, text="Start", command=on_start).grid(row=5, column=0, columnspan=4, pady=10)
    root.mainloop()


if __name__ == '__main__':
    create_gui()