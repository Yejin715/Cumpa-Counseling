
from ..message_event import MessageBroker
from ..async_event import AsyncBroker

class Loggable:
    def __init__(self):
        self.plain_print = False

    def set_tag(self, tag: str) -> None:
        self._tag = tag
    
    def get_tag(self) -> str:
        return self._tag

    def log(self, *args) -> None:
        if self.plain_print:
            print(*args)
        else:
            # print(f"{self._tag}:", *args)
            MessageBroker().emit((f"log {self._tag}", " ".join(str(arg) for arg in args)))