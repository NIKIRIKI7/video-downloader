from commands.download_video import DownloadVideo
from commands.download_subtitles import DownloadSubtitles
from commands.translate_subtitles import TranslateSubtitles
from commands.download_metadata import DownloadMetadata
from commands.translate_metadata import TranslateMetadata
from commands.merge_audio import MergeAudio

class VideoService:
    def __init__(self, logger):
        self.logger = logger

    def perform_actions(self, url, yandex_audio, actions):
        base = None
        context = {"url": url, "yandex_audio": yandex_audio, "base": None}
        for action in actions:
            cmd = self.get_command(action)
            if cmd:
                self.logger(f"▶ {cmd.__class__.__name__}...")
                cmd.execute(context)

    def get_command(self, action):
        mapping = {
            'dv': DownloadVideo,
            'ds': DownloadSubtitles,
            'dt': TranslateSubtitles,
            'md': DownloadMetadata,
            'da': MergeAudio,
        }
        return mapping.get(action, lambda logger: None)(self.logger)