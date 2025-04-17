from commands.base_command import ActionCommand
from deep_translator import GoogleTranslator
import os

class TranslateMetadata(ActionCommand):
    def execute(self, context):
        tr = GoogleTranslator(source='en', target='ru')
        t_title = tr.translate(context['title'])
        t_desc = tr.translate(context['description'])
        t_tags = [tr.translate(t) for t in context['tags']]
        out_dir = "video"
        base = context['base']
        path = os.path.join(out_dir, f"{base}.meta.ru.txt")
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"Title: {t_title}\n\nDescription:\n{t_desc}\n\nTags: {', '.join(t_tags)}")
