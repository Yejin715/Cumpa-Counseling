import os
import sys
import time

from .visual_texture import VideoTexture

class VisualCueTexture:
    """
    A class that provides a visual cue texture for DearPyGui

    Usage:
    ```
    with dpg.child_window(width=480, height=270, parent=chat_window._window) as w:
        self._visual_cue_texture = VisualCueTexture(msg_listener=self).setup(480, 270, texture_tag="visual_cue_texture")
        dpg.add_image("visual_cue_texture")
    ```
    """
    _window: any
    _width: int
    _height: int
    _cumpa_video_state: str
    _video_player: VideoTexture
    _video_files: dict

    def __init__(self):
        self._video_player = VideoTexture()
        
        # Turn taking videos
        TURNTAKING_DIR = "src/graphics/assets/video"
        self._video_files = {
            "NOT_TALKING": os.path.join(TURNTAKING_DIR, "NOT_TALKING.mp4"),
            "LISTENER_RESPONSE": os.path.join(TURNTAKING_DIR, "LISTENER_RESPONSE.mp4"),
            "ATTEMPT_SUPPRESSING": os.path.join(TURNTAKING_DIR, "ATTEMPT_SUPPRESSING.mp4"),
            "THINKING": os.path.join(TURNTAKING_DIR, "THINKING.mp4")
        }
        self._cumpa_video_state = "NOT_TALKING"
    
    def _current_video(self):
        return self._video_files[self._cumpa_video_state]

    def update(self) -> bool:
        return self._video_player.update()

    def setup(self, width: int, height: int, texture_tag: str) -> "VisualCueWindow":
        # Setup the texture
        self._width = width
        self._height = height
        
        self._video_player.setup(width=width, height=height, texture_tag=texture_tag)
        self._video_player.open_video(self._current_video())
        self._video_player.play()        

        return self
    
    # External Callbacks
    def _on_turn_take(self, state: str):
        self._cumpa_video_state = state
        self._video_player.open_video(self._current_video())
        self._video_player.play()