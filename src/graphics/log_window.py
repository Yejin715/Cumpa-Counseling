from datetime import datetime
import dearpygui.dearpygui as dpg

from ..message_event import MessageListener, MessageBroker, MessageType
from ..async_event import AsyncListener, AsyncBroker, AsyncMessageType


class LogWindow:
    _window: any
    _init_width: int

    def __init__(self):
        pass
    
    def setup(self, tag: str, width: int, height: int, x=0, y=0) -> "LogWindow":
        # 
        # Setup the window
        # 
        with dpg.window(label=f"Log: {tag}", width=width, height=height, pos=(x, y)) as w:
            self._window = w
            self._init_width = width
            dpg.add_text("Logs")
        
        # Subscribe events
        AsyncBroker().subscribe(f"log {tag}", self._on_log)
        return self
    
    # 
    # Presentation functions
    #
    def _add_log(self, log: str):
        dpg.add_text(log, bullet=True, parent=self._window, wrap=self._init_width - 10)
    
    # 
    # External Callbacks
    #
    def _on_log(self, msg: AsyncMessageType):
        e, log = msg
        self._add_log(log)