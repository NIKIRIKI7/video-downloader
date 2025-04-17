from model.video_service import VideoService

class VideoViewModel:
    def __init__(self):
        self.listeners = []
        self.service = VideoService(self.log)

    def add_listener(self, listener):
        self.listeners.append(listener)

    def log(self, msg):
        for l in self.listeners:
            l(msg)

    def run(self, url, yandex_audio, actions):
        self.service.perform_actions(url, yandex_audio, actions)