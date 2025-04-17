from abc import ABC, abstractmethod

class ActionCommand(ABC):
    def __init__(self, logger):
        self.log = logger

    @abstractmethod
    def execute(self, context):
        pass