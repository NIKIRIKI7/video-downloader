from commands.base_command import ActionCommand
import subprocess
import json
import os

class DownloadMetadata(ActionCommand):
    def execute(self, context):
        url = context['url']
        out_dir = "video"
        os.makedirs(out_dir, exist_ok=True)
        result = subprocess.check_output(["yt-dlp", "-j", url], text=True)
        data = json.loads(result)
        title = data.get('title', '')
        desc = data.get('description', '')
        tags = data.get('tags', [])
        base = data.get('id', title.replace(' ', '_'))
        context['base'] = base
        context['title'] = title
        context['description'] = desc
        context['tags'] = tags
        meta_path = os.path.join(out_dir, f"{base}.meta.txt")
        with open(meta_path, 'w', encoding='utf-8') as f:
            f.write(f"Title: {title}\n\nDescription:\n{desc}\n\nTags: {', '.join(tags)}")
