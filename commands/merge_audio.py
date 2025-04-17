from commands.base_command import ActionCommand
import subprocess
import os

class MergeAudio(ActionCommand):
    def execute(self, context):
        base = context['base']
        yandex = context['yandex_audio']
        if not base or not yandex:
            return
        video_path = os.path.join("video", f"{base}.mp4")
        out_path = os.path.join("video", f"{base}.mixed.mp4")
        cmd = ["ffmpeg", "-y", "-i", video_path, "-i", yandex,
               "-filter_complex", "[0:a]volume=0.7[a0];[1:a]volume=1[a1];[a0][a1]amix=inputs=2:duration=first[aout]",
               "-map", "0:v", "-map", "[aout]", "-c:v", "copy", "-c:a", "aac", out_path]
        subprocess.run(cmd, check=True)