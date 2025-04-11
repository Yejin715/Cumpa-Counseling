import av
import time
import numpy as np
import dearpygui.dearpygui as dpg

from typing import Any, Iterable

class VideoTexture:
    """
    A class that provides a video texture for DearPyGui
    
    Usage:
    ```
    player = VideoTextureProvider()
    player.setup(width=WIDTH, height=HEIGHT, texture_tag="tag")
    player.open_video('src/graphics/assets/video/LISTENER_RESPONSE.mp4')
    player.play()

    with dpg.child_window(width=width, height=height, border=False):
        dpg.add_image("tag")

    while dpg.is_dearpygui_running():
        player.update():
        dpg.render_dearpygui_frame()
    ```

    """
    _video_gen: Iterable[np.ndarray]
    _start_time: float
    _next_frame: Any
    _frame_time: float
    _raw_data: np.ndarray
    _file: Any
    
    loop: bool
    width: int
    height: int
    texture_tag: str

    def setup(self, loop: bool = True, width: int = 480, height: int = 270, texture_tag: str = "video_texture") -> None:
        self.loop = loop
        self.width = width
        self.height = height
        self.texture_tag = texture_tag

        self._frame_time = 0
        w, h, d = self.width, self.height, 4
        self._raw_data = np.zeros((h, w, d), dtype=np.float32)
        self._raw_data[:, :, 3] = 1.0

        with dpg.texture_registry():
            dpg.add_raw_texture(w, h, self._raw_data, format=dpg.mvFormat_Float_rgba, tag=texture_tag)

        def update_dynamic_texture(new_frame):
            h2, w2, d2 = new_frame.shape
            self._raw_data[:h2, :w2, :3] = new_frame / 255

    def open_video(self, file: Any) -> None:
        self._file = file
        self._video_gen = self._load_frame(file)
    
    def _load_frame(self, file: Any) -> Iterable[np.ndarray]:
        video = av.open(file)
        for frame in video.decode():
            if isinstance(frame, av.VideoFrame):
                frame = frame.reformat(self.width, self.height)
                yield frame.to_ndarray(format='rgb24'), frame.time_base * frame.pts # the second element is the timestamp of the frame in seconds
        video.close()
    
    def play(self):
        self._start_time = time.time()
        self._next_frame, self._frame_time = next(self._video_gen)
    
    def _update_dynamic_texture(self, new_frame: np.ndarray):
        h2, w2, d2 = new_frame.shape
        self._raw_data[:h2, :w2, :3] = new_frame / 255
        dpg.set_value(self.texture_tag, self._raw_data)

    def update(self) -> bool: # returns True if the video is still playing
        current_time = time.time()
        if current_time - self._start_time >= self._frame_time:
            self._update_dynamic_texture(self._next_frame)
            try:
                self._next_frame, self._frame_time = next(self._video_gen)
            except StopIteration:
                if self.loop:
                    self.open_video(self._file)
                    self.play()
                else:
                    return False
        return True