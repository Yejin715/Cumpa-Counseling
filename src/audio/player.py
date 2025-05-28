import urllib.request
import os
import ssl
import pyaudio
import wave
import asyncio
from typing import Tuple, IO, TypedDict

from ..message_event import MessageListener, MessageBroker, MessageType
from ..async_event import AsyncListener, AsyncBroker, AsyncMessageType
from ..lib.loggable import Loggable

class VoiceSettings(TypedDict):
    speaker: str
    volume: int
    speed: int
    pitch: int
    emotion: int
    emotion_strength: int

class ResponsePlayer(Loggable):
    """
    Synthesizes the response (TTS) and plays it.
    """

    # Plan
    # Observe events:
    # - player_push_text (id, text)
    # - player_push_audio (id, text)

    # Emit events:
    # - player_done (id)

    # Current implementation
    # Observe events:
    # - chat_response (text | music-card)
    # Emit events:
    # - play_response_end (id)


    def __init__(self):
        Loggable.__init__(self)
        self.set_tag("response_player")

        self.chat_done_flag = False

        # Load the environment variables
        self._clova_client_id = os.getenv("CLOVA_TTS_CLIENT_ID")
        self._clova_client_secret = os.getenv("CLOVA_TTS_CLIENT_SECRET")

        # Set clova TTS settings
        self._default_voice_settings = VoiceSettings(
            speaker=os.getenv("CLOVA_SPEAKER") or "vdonghyun", # https://api.ncloud-docs.com/docs/ai-naver-clovavoice-ttspremium
            volume=0,
            speed=0,
            pitch=0,
            emotion=0,
            emotion_strength=2,
            format="wav",
            sampling_rate=48000,
        )

        # Ignore SSL certificate errors
        # TODO: This line must be removed before deployment for security reasons.
        ssl._create_default_https_context = ssl._create_unverified_context 

        # Initialize the pyaudio stream
        self.pa = pyaudio.PyAudio()
        self._stream = None

        # Register event handlers
        AsyncBroker().subscribe("wait_chat_finish", self._on_wait_chat_finish)
        AsyncBroker().subscribe("chat_response", self._on_chat_response)
        AsyncBroker().subscribe("wake_up", self._on_wake_up)
    
    def _on_wait_chat_finish(self, msg: AsyncMessageType):
        print("Chat finished, closing the stream.")
        self.chat_done_flag = True

    def _check_stream_end(self):
        if self._stream is not None and not self._stream.is_active():
            self._stream.close()
            self._stream = None
            AsyncBroker().emit(("play_response_end", None))

    def map_emotion_to_value(self, emotion_label: str = None) -> int:
        emotion_value_map = {
        "중립": 0,
        "슬픔": 1,
        "화남": 3,
        "부정": 3,
        "짜증난": 1,
        "기쁨": 2
        }

        # Map the emotion label to its corresponding value
        return emotion_value_map.get(emotion_label, 0)

    async def _on_chat_response(self, response: dict):
        emotion_label = response.get('emotion', "중립")  # 기본값 중립

        if response.get('type') in [None, "text"]:
            # 감정 분석 결과 확인
            clova_emotion = self.map_emotion_to_value(emotion_label)
            self.log(f"Emotion label: {emotion_label}, emotion value: {clova_emotion}")
            # TTS 요청에서 emotion 값 설정
            self._make_audio(response['msg'], emotion=clova_emotion)
            await self._play_audio("text.wav")
        elif response.get('type') == "music-card":
            music_name = response['msg']['src']  # e.g. "eno1.wav"
            music_path = f"src/audio/assets/music/{music_name}" # e.g. "assets/music/eno1.wav"
            await self._play_audio(music_path)
        elif response.get('type') == "sound":
            sound_name = response['msg']  # e.g. "sound/backchanneling.wav"
            sound_path = f"src/audio/assets/{sound_name}" 
            await self._play_audio(sound_path)
        elif response.get('type') == "audio-cue":
            sound_name = response['msg'] # e.g. "assets/music/ding.wav"
            sound_path = f"src/audio/assets/music/{sound_name}" 
            await self._play_audio(sound_path)
        else:
            self.log(f"Unknown response type {response['type']}")
            AsyncBroker().emit(("play_response_end", None))
    
    async def _play_audio(self, f: IO):
        """
        play the audio file with {filename}
        """
        try:
            wf = wave.open(f, 'rb')
            self.log(f, wf.getframerate(), wf.getsampwidth(),
                    self.pa.get_format_from_width(wf.getsampwidth()))

            def callback(in_data, frame_count, time_info, status):
                data = wf.readframes(frame_count)
                if len(data) == 0 or wf.tell() == wf.getnframes():
                    wf.close()
                    # 스트림이 끝나면 이벤트 발행
                    print("self.chat_done_flag", self.chat_done_flag)
                    if self.chat_done_flag:
                        AsyncBroker().emit(("chat_done", None))
                    else:
                        AsyncBroker().emit(("chat_listening_start", None))
                    return (data, pyaudio.paComplete)
                return (data, pyaudio.paContinue)

            self._stream = self.pa.open(format=self.pa.get_format_from_width(wf.getsampwidth()),
                                        channels=wf.getnchannels(),
                                        rate=wf.getframerate(),
                                        output=True,
                                        frames_per_buffer=2048,
                                        stream_callback=callback)

        except (FileNotFoundError, wave.Error) as e:
            self.log(f"Failed to open the audio file {f}: {e}")

    def _make_audio(self, text: str, emotion: int = 0, **settings: VoiceSettings) -> None:
        """
        Make audio with {text} using naver clova TTS.
        Return the bytes of the audio file.
        """

        # Clova API auth
        ENDPOINT = "https://naveropenapi.apigw.ntruss.com/tts-premium/v1/tts"
        request = urllib.request.Request(ENDPOINT)
        request.add_header("X-NCP-APIGW-API-KEY-ID", self._clova_client_id)
        request.add_header("X-NCP-APIGW-API-KEY", self._clova_client_secret)

        # Construct query
        s = { **self._default_voice_settings }
        s["emotion"] = emotion  # 감정 값 동적으로 설정
        s.update(settings)
        self.log(f"_make_audio emotion: {emotion}")
        
        query = f"speaker={s['speaker']}" + \
               f"&volume={s['volume']}" + \
               f"&speed={s['speed']}" + \
               f"&pitch={s['pitch']}" + \
               f"&emotion={s['emotion']}" + \
               f"&emotion-strength	={s['emotion_strength']}" + \
               "&format=wav" + \
               "&sampling-rate=48000" + \
               f"&text={urllib.parse.quote(text)}"

        try:
            # Make the request to the API
            response = urllib.request.urlopen(request, data=query.encode('utf-8'))
            rescode = response.getcode()

            if rescode == 200:
                # Return the audio file as bytes
                response_body = response.read()
                with open('text.wav', 'wb') as f:
                    f.write(response_body)
                return
            else:
                self.log(f"Failed to synthesize speech. HTTP response code: {rescode}")
                self.log(f"Response: {response.read()}")
                # TODO: write empty audio to text.wav
                return

        except urllib.error.HTTPError as e:
            # Log HTTPError with all the details
            self.log(f"HTTPError occurred: {e.code} - {e.reason}")
            self.log(f"Headers: {e.headers}")
            self.log(f"Response: {e.read()}")
            # TODO: write empty audio to text.wav
            return

        except urllib.error.URLError as e:
            # Log URLError (e.g., failed to reach the server)
            self.log(f"URLError occurred: {e.reason}")
            # TODO: write empty audio to text.wav
            return
        
    async def _on_wake_up(self, _: tuple[str, None]):
        self.log("Wake Up")
        self.chat_done_flag = False

        sound_path = f"src/audio/assets/music/ding.wav" 
        await self._play_audio(sound_path)

    def stop(self):
        self.pa.terminate()