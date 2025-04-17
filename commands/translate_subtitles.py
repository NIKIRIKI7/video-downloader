from commands.base_command import ActionCommand
import pysubs2
from deep_translator import GoogleTranslator
import os

class TranslateSubtitles(ActionCommand):
    def execute(self, context):
        base = context['base']
        path = os.path.join("video", f"{base}.en.vtt")
        out_path = os.path.join("video", f"{base}.ru.vtt")
        subs = pysubs2.load(path, encoding="utf-8")
        tr = GoogleTranslator(source='en', target='ru')
        for line in subs:
            line.text = tr.translate(line.text)
        subs.save(out_path, format_='vtt')