import dearpygui.dearpygui as dpg

from ..lib.time_stamp import get_current_timestamp
from ..message_event import MessageBroker, MessageType
from ..async_event import AsyncBroker, AsyncMessageType


class ChatWindow:
    _window: any
    _width: int 
    _height: int
    use_whisper =  False  # 기본은 Whisper 사용 (현재는 꺼놓은 상황)

    def __init__(self):
        self.keyboard_start_time = 0

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
                self._el_recording_label = dpg.add_text("Recording...", show=False)
                self._el_recording_indicator = dpg.add_loading_indicator(show=False)
                # 내용이 길어지면 기본적으로 스크롤바가 생깁니다.
            dpg.add_checkbox(label="음성인식사용여부 (미사용시 키보드 입력)", default_value=ChatWindow.use_whisper, callback=self._on_toggle_whisper)

            # 입력 영역 (라벨과 입력창)
            with dpg.group(horizontal=True):
                dpg.add_text("입력 : ")
                dpg.add_input_text(tag="user_input", hint="전달하고 싶은 내용을 작성하세요.", )
                dpg.add_button(label="Send", callback=self._on_send)
            dpg.add_button(label="Wake up", callback=self._on_wakeup_btn)
            dpg.add_button(label="Stop conversation", callback=self._on_stop)

            # Subscribe event
            AsyncBroker().subscribe("chat_response", self._on_chat_response)
            AsyncBroker().subscribe("chat_listening_start", self._on_chat_listening_start)
            AsyncBroker().subscribe("chat_user_input", self._on_chat_user_input)
            AsyncBroker().subscribe("chat_done", self._on_chat_done)
            AsyncBroker().subscribe("chat_done_listening", self._on_chat_done_listening)
            
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
        # print("user msg:", msg)
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
        dpg.set_value("user_input", "")
        end_time = get_current_timestamp()

        AsyncBroker().emit(("chat_cycle_time", {"content": "KEYBOARD MODE", "start_time": self.keyboard_start_time, "end_time": end_time}))
        AsyncBroker().emit(("chat_user_input", {"content": user_input, "start_time": end_time, "end_time": end_time}))

    def _on_wakeup_btn(self):
        AsyncBroker().emit(("wake_up", None))

    def _on_stop(self):
        AsyncBroker().emit(("chat_done", None))

    def _on_toggle_whisper(self, sender, app_data, user_data=None):
        ChatWindow.use_whisper = app_data  # True면 Whisper 사용, False면 키보드 입력
        if ChatWindow.use_whisper:
            AsyncBroker().emit(("cumpa_listening_start", None))
        
    # External Callbacks
    def _on_chat_response(self, response: dict):
        dpg.configure_item(self._el_loading, show=False)

        if response['type'] =="text" or response['type'] == "meta":
            self._add_bot_msg(response['msg'])
            # AsyncBroker().emit(("chat_listening_start", None))
        elif response['type'] == "music-card":
            self._add_bot_msg(f"Playing {response['msg']['src']} ...")
            # AsyncBroker().emit(("chat_listening_start", None))
        else:
            print(f"Unknown response type {response['type']}")

    def _on_chat_user_input(self, msg: dict):
        user_input = msg['content']
        self._add_user_msg(user_input)
        dpg.configure_item(self._el_recording_label, show=False)
        dpg.configure_item(self._el_recording_indicator, show=False)

    def _on_chat_listening_start(self, msg: AsyncMessageType):
        dpg.configure_item(self._el_recording_label, show=True)
        dpg.configure_item(self._el_recording_indicator, show=True)
        self.keyboard_start_time = get_current_timestamp()
    
    def _on_chat_done(self, msg: AsyncMessageType):
        dpg.configure_item(self._el_recording_label, show=False)
        dpg.configure_item(self._el_recording_indicator, show=False)
        dpg.configure_item(self._el_loading, show=False)
        AsyncBroker().emit(("chat_done_listening", None))

    def _on_chat_done_listening(self, msg: AsyncMessageType):
        self._add_bot_msg("(대화 마침_'친구님 대화하자'인식 시작)")