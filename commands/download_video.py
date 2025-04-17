from commands.base_command import ActionCommand
import subprocess
import os

class DownloadVideo(ActionCommand):
    def execute(self, context):
        url = context['url']
        out_dir = "video"
        os.makedirs(out_dir, exist_ok=True)
        cmd = ["yt-dlp", "--format", "bestvideo+bestaudio/best", "--merge-output-format", "mp4",
               "--write-description", "--write-sub", "--sub-lang", "en", "--convert-subs", "vtt",
               "-o", os.path.join(out_dir, "%(title)s.%(ext)s"), url]
        subprocess.run(cmd, check=True)
        for f in os.listdir(out_dir):
            if f.endswith(".mp4"):
                context['base'] = os.path.splitext(f)[0]
                return

