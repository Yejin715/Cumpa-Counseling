import os
import sys
import time

from .visual_texture import VideoTexture
from ..message_event import MessageBroker, MessageType
from ..async_event import AsyncBroker, AsyncMessageType

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
        self._is_turn_taking = False  # 추가된 플래그: Turn Taking 상태 확인
        self._is_updating = False  # 제너레이터 실행 중 여부
        self._turn_take_queue = []  # 실행 대기 중인 _on_turn_take 함수들
        
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
        # update가 실행 중일 때는 _on_turn_take가 대기하도록 함
        if self._is_turn_taking:
            return False
        
        if self._is_updating:
            return True  # 동영상 업데이트 계속 진행
        
        try:
            self._is_updating = True  # 업데이트 시작

            # 실제 update가 필요한 부분
            result = self._video_player.update()

            # update가 끝났다면 대기 중인 _on_turn_take이 있으면 실행
            if self._turn_take_queue:
                next_turn = self._turn_take_queue.pop(0)
                next_turn()

            return result

        finally:
            self._is_updating = False  # 제너레이터 실행이 끝났으면 플래그 초기화


    def setup(self, width: int, height: int, texture_tag: str) -> "VisualCueTexture":
        # Setup the texture
        self._width = width
        self._height = height
        
        self._video_player.setup(width=width, height=height, texture_tag=texture_tag)
        self._video_player.open_video(self._current_video())
        self._video_player.play()

        # Subscribe event
        AsyncBroker().subscribe("chat_start_new", lambda _: self._on_turn_take("ATTEMPT_SUPPRESSING"))
        AsyncBroker().subscribe("chat_listening_start", lambda _: self._on_turn_take("LISTENER_RESPONSE"))
        AsyncBroker().subscribe("chat_user_input", lambda _: self._on_turn_take("THINKING"))
        AsyncBroker().subscribe("chat_done", lambda _: self._on_turn_take("NOT_TALKING"))
        AsyncBroker().subscribe("chat_response", lambda _: self._on_turn_take("ATTEMPT_SUPPRESSING"))
        
        return self
    
    # External Callbacks
    def _on_turn_take(self, state: str):
        # update가 실행 중일 때는 _on_turn_take이 대기하도록 큐에 추가
        if self._is_updating:
            self._turn_take_queue.append(lambda: self._execute_turn_take(state))  # 대기 큐에 추가
        else:
            self._execute_turn_take(state)  # 바로 실행

    def _execute_turn_take(self, state: str):
        # _on_turn_take 실행 함수
        self._is_turn_taking = True  # Turn taking 시작
        self._cumpa_video_state = state
        print(f"VisualCueTexture: {state}")
        self._video_player.open_video(self._current_video())
        self._video_player.play()

        self._is_turn_taking = False  # Turn taking 상태 종료