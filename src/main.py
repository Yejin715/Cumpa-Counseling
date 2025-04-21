import os  #Python 내장 모듈 불러오기
import threading
import time

from dotenv import load_dotenv

from .lib.loggable import Loggable
from .graphics.graphics import Graphics
  
load_dotenv()

class Core(threading.Thread, Loggable):
    
    def __init__(self):
        threading.Thread.__init__(self)
        Loggable.__init__(self)
        self.set_tag("core")

        self.TARGET_DEVICE = os.getenv("TARGET_DEVICE", "PC") # RPi or PC
    
    def get_log_tags(self):
        return self.get_tag()
        return [
            self.get_tag(),
            *[t.get_tag() for t in self.threads]
        ]
    
    def run(self):
        self.log("Core started")

    def stop(self):
        self.cleanup()
    
    def cleanup(self):
        self.log("Cleaning up")

if __name__ == "__main__":
    core = Core()
    core.start()
    
    gui = Graphics()
    gui.run(log_tags=core.get_log_tags())