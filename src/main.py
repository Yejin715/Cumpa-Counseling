import os  #Python 내장 모듈 불러오기
import threading
import time

from dotenv import load_dotenv
from .lib.microphone import pa as mic_pa

from .lib.loggable import Loggable
from .audio.player import ResponsePlayer
from .graphics.graphics import Graphics
from .message_event import MessageListener
from .async_event import AsyncListener
from .dialog_manager.llm_chatgpt import LLMChatManager
from .dialog_manager.faster_whisper_recognizer import FasterWhisperRecognizer

  
load_dotenv()

class Core(threading.Thread, Loggable):
    
    def __init__(self):
        threading.Thread.__init__(self)
        Loggable.__init__(self)
        self.set_tag("core")

        self.TARGET_DEVICE = os.getenv("TARGET_DEVICE", "PC") # RPi or PC
        self.response_player = ResponsePlayer()
        self.llm_chat = LLMChatManager()
        self.speech_recognizer = FasterWhisperRecognizer(model_size="base")  # Faster-Whisper로 변경
        # self.threads = (self.llm_chat, self.speech_recognizer)
        self.threads = (self.llm_chat,)

    def get_log_tags(self):
        return [self.get_tag()]
        return [
            self.get_tag(),
            *[t.get_tag() for t in self.threads]
        ]
    
    def run(self):
        self.log("Core started")
        for thread in self.threads:
            thread.start()
        try:
            AsyncListener().run()
        except KeyboardInterrupt:
            self.cleanup()
        except:
            self.cleanup()
            raise
    
    def stop(self):
        self.cleanup()
    
    def cleanup(self):
        self.log("Cleaning up")
        # Producers should be stopped at last because the consumers may be blocked.
        for thread in self.threads:
            thread.stop()
        for thread in self.threads:
            thread.join()
        mic_pa.terminate()
        self.log("Cleaned up")

if __name__ == "__main__":
    core = Core()
    core.start()
    
    gui = Graphics()
    gui.run(log_tags=core.get_log_tags())