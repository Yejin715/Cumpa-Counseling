# async_event.py
import os
import asyncio
from dotenv import load_dotenv
from collections import OrderedDict
from threading import Thread
from typing import Dict, Set, TypeVar, Callable, Tuple, Any, Awaitable
import inspect

T = TypeVar("T")
AsyncMessageType = Tuple[str, T]     # (event_name, payload)

load_dotenv()
class AsyncListener:
    """
    ■ 논블로킹 메시지 처리 리스너 ■
    - 자신의 asyncio.Queue 에 메시지를 저장
    - run() 코루틴으로 꺼내 handle() 호출
    - 구독/발행은 오직 AsyncBroker 에서만!
    """
    def __init__(self, max_queue_size: int = 10):
        self.queue: asyncio.Queue[AsyncMessageType] = asyncio.Queue(max_queue_size)
        self._running = False

    async def enqueue(self, message: AsyncMessageType):
        try:
            self.queue.put_nowait(message)
        except asyncio.QueueFull:
            pass  # overflow 시 drop

    async def run(self):
        self._running = True
        while self._running:
            event, detail = await self.queue.get()
            try:
                await self.handle(event, detail)
            except Exception as e:
                print(f"[AsyncListener] handle error for {event}: {e}")

    def stop(self):
        self._running = False

    async def handle(self, event: str, detail: Any):
        """
        ■ 서브클래스에서 구현할 부분
        """
        raise NotImplementedError("서브클래스에서 handle() 을 구현하세요.")


class AsyncCallbackListener(AsyncListener):
    """
    ■ 단일 콜백 처리 전용 리스너 ■
    - 콜백 함수만 넘겨도 자동 래핑
    """
    def __init__(self,
                 callback: Callable[[Any], Awaitable],
                 max_queue_size: int = 10):
        super().__init__(max_queue_size)
        self._callback = callback
        # 백그라운드 루프에서 run() 코루틴 자동 실행
        asyncio.run_coroutine_threadsafe(self.run(),
                                         AsyncBroker()._loop)

    async def handle(self, event: str, detail: Any):
        # 1) 콜백 실행
        result = self._callback(detail)
        # 2) 만약 coroutine/awaitable이라면 await!
        if inspect.isawaitable(result):
            await result
        # 동기 함수면 그냥 반환(None)하면서 끝


class AsyncBroker:
    """
    ■ 중앙 Async 이벤트 브로커 (싱글톤) ■
    - subscribe/emit 모두 동기 메서드로 안전하게 호출 가능
    - 자체 전용 asyncio 이벤트 루프를 백그라운드에서 실행
    """
    _instance = None

    def __new__(cls):
        if not cls._instance:
            inst = super().__new__(cls)
            inst._events: Dict[str, Set[AsyncListener]] = OrderedDict()
            inst._lock = asyncio.Lock()
            inst.VERBOSE =  os.getenv("Debugging_Mode", "False")  # 디버깅용

            # 1) 전용 이벤트 루프 생성
            inst._loop = asyncio.new_event_loop()
            # 2) 백그라운드 스레드에서 run_forever()
            t = Thread(target=inst._loop.run_forever, daemon=True)
            t.start()

            cls._instance = inst
        return cls._instance

    def subscribe(self,
                  event: str,
                  listener: Callable[[Any], Awaitable] | AsyncListener,
                  max_queue_size: int = 10):
        """
        ■ 동기 메서드
        - 함수나 메서드를 넘기면 AsyncCallbackListener로 래핑
        """
        # 실제 코루틴 작업을 백그라운드 루프에 스케줄
        asyncio.run_coroutine_threadsafe(
            self._subscribe_coro(event, listener, max_queue_size),
            self._loop)

    async def _subscribe_coro(self,
                              event: str,
                              listener: Callable[[Any], Awaitable] | AsyncListener,
                              max_queue_size: int):
        async with self._lock:
            if not isinstance(listener, AsyncListener):
                # 함수·메서드·코루틴함수 → 래핑
                if (inspect.isfunction(listener)
                        or inspect.ismethod(listener)
                        or inspect.iscoroutinefunction(listener)):
                    listener = AsyncCallbackListener(listener,
                                                     max_queue_size)
                else:
                    raise ValueError(
                        "구독자는 AsyncListener 인스턴스 또는 콜백이어야 합니다."
                    )
            self._events.setdefault(event, set()).add(listener)
            if self.VERBOSE:
                print(f"[AsyncBroker] '{event}' subscribed by {listener}")

    def unsubscribe(self, event: str, listener: AsyncListener):
        """
        ■ 동기 메서드
        """
        asyncio.run_coroutine_threadsafe(
            self._unsubscribe_coro(event, listener), self._loop)

    async def _unsubscribe_coro(self, event: str, listener: AsyncListener):
        async with self._lock:
            if event in self._events:
                self._events[event].discard(listener)
                if not self._events[event]:
                    del self._events[event]

    def emit(self, message: AsyncMessageType):
        """
        ■ 동기 메서드
        """
        asyncio.run_coroutine_threadsafe(self._emit_coro(message),
                                         self._loop)

    async def _emit_coro(self, message: AsyncMessageType):
        event, detail = message
        if self.VERBOSE:
            print(f"[AsyncBroker] Emit '{event}': {detail}")

        async with self._lock:
            listeners = list(self._events.get(event, []))

        # 실제 listener.enqueue는 async 메서드이므로 Task로 스케줄
        for listener in listeners:
            asyncio.create_task(listener.enqueue((event, detail)))
