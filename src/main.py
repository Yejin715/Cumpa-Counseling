import os  #Python 내장 모듈 불러오기
import threading
import time

from dotenv import load_dotenv
from .lib.microphone import pa as mic_pa

from .lib.loggable import Loggable
from .graphics.graphics import Graphics
from .message_event import MessageListener
from .async_event import AsyncListener
from .dialog_manager.faster_whisper_recognizer import FasterWhisperRecognizer

  
load_dotenv()

class Core(threading.Thread, Loggable):
    
    def __init__(self):
        threading.Thread.__init__(self)
        Loggable.__init__(self)
        self.set_tag("core")

        self.TARGET_DEVICE = os.getenv("TARGET_DEVICE", "PC") # RPi or PC
        self.speech_recognizer = FasterWhisperRecognizer(model_size="base")  # Faster-Whisper로 변경
        self.threads = self.speech_recognizer

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
            MessageListener().run(self)
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