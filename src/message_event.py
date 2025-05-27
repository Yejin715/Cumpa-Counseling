from threading import Thread, Lock
from queue import Queue, Full, Empty
from collections import OrderedDict
from typing import Dict, Set, TypeVar, Callable, Tuple, Any, List
from .lib.singleton import Singleton
import time
import os
from dotenv import load_dotenv

T = TypeVar("T")
MessageType = Tuple[str, T]               # (event_name, payload)
ListenerThread = TypeVar("ListenerThread", bound="MessageListener")

load_dotenv()
class MessageListener(Thread):
    """
    ■ 메시지 처리 전용 스레드 ■
    - enqueue() 로 메시지를 받아 자신의 큐에 보관
    - run() 루프에서 큐를 비우며 handle() 호출
    - 구독/발행은 브로커에게만 맡깁니다!
    """
    def __init__(self):
        Thread.__init__(self)
        self._stop_flag = False
        # 각 메시지를 저장할 큐 (최대 10개 큐잉)
        self.message_queue: Queue[MessageType] = Queue(maxsize=10)
        # 이벤트 루프 빈도로 지정 (초 단위)
        self._loop_time = 1.0 / 60

    def enqueue(self, message: MessageType):
        """
        ■ 브로커가 메시지를 전달할 때 호출
        ■ 메시지를 큐에 넣고, overflow 시에는 drop
        """
        try:
            self.message_queue.put_nowait(message)
        except Full:
            # 큐가 가득 찼다면 별도 로깅 없이 무시(드롭)
            pass
    
    def run(self):
        """
        ■ Thread.start() 시 자동 실행되는 메인 루프
        1) 지정된 주기마다 _handle_events() 호출 → 큐 비우기
        2) idle() 호출 → 추가 여유 작업 (오버라이드 가능)
        """
        while not self._stop_flag:
            self._handle_events()
            self.idle()
            time.sleep(self._loop_time)


    def stop(self):
        """■ 루프를 중단하도록 플래그 설정"""
        self._stop_flag = True

    def _handle_events(self):
        """
        ■ 큐에서 처리 대기 중인 모든 메시지 꺼내기
        ■ 각 메시지(event, detail)에 등록된 handle() 호출
        """
        while True:
            try:
                event, detail = self.message_queue.get_nowait()
                self.handle(event, detail)
            except Empty:
                # 큐가 비어 있으면 루프 종료
                break

    def idle(self):
        """
        ■ 이벤트 처리 후 호출되는 여유 작업 메서드
        ■ 오버라이드하여 추가 로직 수행 가능
        ■ 실행 시간이 길면 전체 루프가 느려지니 주의
        """
        pass

    def handle(self, event: str, detail: Any):
        """
        ■ 서브클래스에서 반드시 구현할 부분
        ■ 실제 이벤트별 처리 로직 작성
        """
        raise NotImplementedError(
            "서브클래스에서 handle(event, detail)을 구현해야 합니다."
        )

            
class CallbackListener(MessageListener):
    """
    ■ 단일 콜백 처리 전용 리스너 ■
    - subscribe() 에 함수나 메서드를 넘기면
      내부에서 이 클래스로 자동 래핑합니다.
    """
    def __init__(self, callback: Callable[[Any], None], queue_size: int = 10):
        super().__init__()
        # 원하는 큐 크기로 재설정
        self.message_queue = Queue(maxsize=queue_size)
        self._callback = callback
        self.start()

    def handle(self, event: str, detail: Any):
        # detail 만 콜백에 전달
        self._callback(detail)

class MessageBroker(Singleton):
    """
    ■ 중앙 이벤트 브로커 (싱글톤) ■
    - 전역 한 곳에서만 인스턴스화되어 사용
    - subscribe/unsubscribe/emit 모두 thread-safe 보장
    - 구독자 관리 및 메시지 라우팅 역할 수행
    """
    def _init(self) -> None:
        print("Message broker: init")
        # event_name → {ListenerThread, ...} 매핑
        self._events: Dict[str, Set[ListenerThread]] = OrderedDict()
        # 동시성 문제 방지를 위한 락
        self._lock = Lock()
        # 디버깅 시 구독자 현황 출력 여부
        self.VERBOSE_CURRENT_SUBSCRIBERS = os.getenv("Debugging_Mode", "False")  # 디버깅용


    def subscribe(self, event: str, listener: ListenerThread):
        """
        ■ 이벤트에 listener 등록 (thread-safe)
        1) 락 획득 후 _events 딕셔너리 수정
        2) event 키가 없으면 빈 Set 생성, listener 추가
        3) verbose 모드면 구독 상태 로깅
        """
        with self._lock:
            from inspect import isfunction, ismethod
            if isfunction(listener) or ismethod(listener):
                listener = CallbackListener(listener)
            self._events.setdefault(event, set()).add(listener)
            
            if self.VERBOSE_CURRENT_SUBSCRIBERS:
                print(f"💌: \033[1m{event}\033[0m was subscribed by \033[1m{listener}\033[0m")
                print("\t\033[1msubscribers:\033[0m", self._events)

    def unsubscribe(self, event: str, listener: ListenerThread) -> None:
        """
        ■ 이벤트 구독 해제 + 키 정리 (thread-safe)
        1) 락 획득 후 listener 제거 (discard → 예외 방지)
        2) 남은 구독자가 없으면 해당 event 키 삭제
        """
        with self._lock:
            if event in self._events:
                self._events[event].discard(listener)  # remove 대신 discard
                if not self._events[event]:
                    del self._events[event]

    def emit(self, message: MessageType) -> None:
        """
        ■ 이벤트 발행 (thread-safe)
        1) verbose 모드면 로그 출력
        2) 락 안에서 현재 구독자 목록만 스냅샷 복사
        3) 락 해제 후 각 listener.enqueue() 호출
        """
        event, detail = message

        # 1) 디버그 로그 (verbose 모드에서만)
        if self.VERBOSE_CURRENT_SUBSCRIBERS:
            print("\n💌:", event, "\n\033[1mdetail:\033[0m", detail)

        # 2) 락 안에서 구독자 목록 복사 (임계 구역 최소화)
        with self._lock:
            listeners = list(self._events.get(event, []))

        # 3) 락 해제 후 메시지 전달
        for listener in listeners:
            listener.enqueue((event, detail))
