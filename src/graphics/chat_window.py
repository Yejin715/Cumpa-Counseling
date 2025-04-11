import dearpygui.dearpygui as dpg
import os


class ChatWindow:
    _window: any
    _width: int
    _height: int

    def __init__(self):
        pass
    def setup(self, width: int, height: int, title_bar: bool) -> "ChatWindow":
        # Setup the window
        with dpg.window(label="", width=width, height=height, no_title_bar=title_bar) as w:
            self._window = w
            self._width = width
            self._height = height
            dpg.add_text("대화 내용")
            # 고정 크기의 채팅 기록 영역을 child_window로 생성
            CHAT_AREA_HEIGHT = int(height * 0.3)  # 예: 전체 창 높이의 60% 정도로 설정
            with dpg.child_window(width=width - 20, height=CHAT_AREA_HEIGHT, border=True) as chat_area:
                self._chat_area = chat_area  # 여기서 저장해둠
                self._el_loading = dpg.add_loading_indicator()
                # 내용이 길어지면 기본적으로 스크롤바가 생깁니다.
            
            # 입력 영역 (라벨과 입력창)
            with dpg.group(horizontal=True):
                dpg.add_text("입력 : ")
                dpg.add_input_text(tag="user_input", hint="전달하고 싶은 내용을 작성하세요.", )
            dpg.add_button(label="Send", callback=self._on_send)
            dpg.add_button(label="Wake up", callback=self._on_wakeup_btn)
            dpg.add_button(label="Stop conversation", callback=self._on_stop)
            self._el_recording_label = dpg.add_text("Recording...", show=False)
            self._el_recording_indicator = dpg.add_loading_indicator(show=False)
        return self

    #
    # Presentation functions
    #
    def _add_bot_msg(self, msg: str):
        dpg.add_text(f"cumpa: {msg}", bullet=True, before=self._el_loading, parent=self._chat_area,
                     wrap=self._width - 50)
        # 채팅 영역의 스크롤을 최하단으로 설정
        dpg.set_y_scroll(self._chat_area, 999999)

    def _add_user_msg(self, msg: str):
        dpg.add_text(f"user: {msg}", bullet=True, before=self._el_loading, parent=self._chat_area,
                     wrap=self._width - 50)
        # 채팅 영역의 스크롤을 최하단으로 설정
        dpg.set_y_scroll(self._chat_area, 999999)

    #
    # UI Callbacks
    #
    def _on_send(self):
        dpg.configure_item(self._el_loading, show=True)
        user_input = dpg.get_value("user_input")
        if user_input == "":
            user_input = "안녕하세요."
        else:
            print("입력값:", user_input)
        dpg.set_value("user_input", "")
        ChatWindow._on_chat_user_input(self, ("chat_user_input", user_input))

    def _on_wakeup_btn(self):
        dpg.configure_item(self._el_loading, show=False)

    def _on_stop(self):
        dpg.configure_item(self._el_loading, show=True)        

    def _on_chat_user_input(self, msg: tuple[str, str]):
        _, user_input = msg
        self._add_user_msg(user_input)
        dpg.configure_item(self._el_recording_label, show=False)
        dpg.configure_item(self._el_recording_indicator, show=False)