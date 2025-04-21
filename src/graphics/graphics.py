import os
import sys
from typing import List
from dotenv import load_dotenv
import dearpygui.dearpygui as dpg


from ..lib.singleton import Singleton
from .chat_window import ChatWindow
from .log_window import LogWindow
from .visual_cue_texture import VisualCueTexture

load_dotenv()
class Graphics(Singleton):
    ASSETS_PATH = "src/graphics/assets/"
    _visual_cue_texture: VisualCueTexture
    _log_tags: List[str]

    def __init__(self):
        self.RUN_DEVICE = os.getenv("TARGET_DEVICE", "PC") # RPi or PC
        self.VISUAL_CUE_ONLY = True if self.RUN_DEVICE == "RPi" else False

        self.WIDTH = 800 if self.RUN_DEVICE == "RPi" else 800
        self.HEIGHT = 470 if self.RUN_DEVICE == "RPi" else 600
            
    def _setup_font(self):
        # 한글 폰트 사용하기 위해 폰트 설정
        with dpg.font_registry():
            with dpg.font(os.path.join(self.ASSETS_PATH, "neodgm_code.ttf"), 16, default_font=True) as font:
                dpg.add_font_range_hint(dpg.mvFontRangeHint_Korean)
                dpg.bind_font(font)
        
    def run(self, log_tags: List[str] = []):
        # 초기화 및 기본 컨텍스트 생성
        dpg.create_context()
        
        # 뷰포트(윈도우) 생성 및 설정
        self._setup_font()
        dpg.create_viewport(title='Cumpa', width=self.WIDTH, height=self.HEIGHT)
        dpg.setup_dearpygui()
        
        # Setup the windows
        if not self.VISUAL_CUE_ONLY:
            # 일반 모드: ChatWindow 생성 및 추가 child window 구성
            log_width = 300
            chat_window = ChatWindow().setup(self.WIDTH - log_width, self.HEIGHT, True)
            with dpg.child_window(width=480, height=270, parent=chat_window._window) as w:
                self._visual_cue_texture = VisualCueTexture().setup(480, 270, texture_tag="visual_cue_texture")
                dpg.add_image("visual_cue_texture")
                
            for (i, tag) in enumerate(log_tags):
                height = self.HEIGHT // len(log_tags)
                LogWindow().setup(tag, log_width, height, x=self.WIDTH - log_width, y=height * i)
        
        else:
            # Visual Cue 전용 모드: "Ways of talking" 창 생성
            with dpg.window(label="Ways of talking", tag="Ways of talking", width=self.WIDTH, height=self.HEIGHT) as w:
                self._visual_cue_texture = VisualCueTexture().setup(self.WIDTH, self.HEIGHT, texture_tag="visual_cue_texture")
                dpg.add_image("visual_cue_texture")
            dpg.toggle_viewport_fullscreen()
            dpg.set_primary_window("Ways of talking", True)

        # 뷰포트 보여주기
        dpg.show_viewport()

        # 메인 이벤트 루프 실행 (사용자가 창을 닫을 때까지 유지)
        # dpg.start_dearpygui()
        
        # 메인 이벤트 루프 실행
        self._render_loop()

        # 메인 루프 종료 후 컨텍스트 정리
        dpg.destroy_context()
    
    def _render_loop(self):
        while dpg.is_dearpygui_running():
            self._visual_cue_texture.update()
            dpg.render_dearpygui_frame()