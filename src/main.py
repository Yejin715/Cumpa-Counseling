import os  #Python 내장 모듈 불러오기

from dotenv import load_dotenv

from .graphics.graphics import Graphics
  
load_dotenv()
if __name__ == "__main__":
    gui = Graphics()
    gui.run()