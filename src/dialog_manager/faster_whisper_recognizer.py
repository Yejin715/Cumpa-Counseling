"""
A module that recognizes the user's speech using OpenAI Whisper.
"""
import numpy as np
from faster_whisper import WhisperModel
from threading import Event, Thread
import webrtcvad
import wave
from io import BytesIO

from ..lib.time_stamp import get_current_timestamp
from ..lib.microphone import Microphone
from ..lib.loggable import Loggable
from ..message_event import MessageListener, MessageBroker, MessageType
from ..async_event import AsyncListener, AsyncBroker, AsyncMessageType
from ..graphics.chat_window import ChatWindow


class FasterWhisperRecognizer(Loggable):
    """
    Recognizes the user's speech using OpenAI Whisper.
    """

    TEST_MODE = False  # 테스트 모드 활성화 (독립 실행 시 True)

    def __init__(self, model_size="base", device="cpu", compute_type="int8"):
        """
        Initialize the WhisperRecognizer with a shared model.
        :param model_size: Whisper model size ('tiny', 'base', 'small', etc.)
        """
        Loggable.__init__(self)
        self.set_tag("speech_recognizer")

        self._mic_end = Event()
        self._recognize_thread = None
        self.whisper_start_time = 0

        # 메시지 구독
        AsyncBroker().subscribe("cumpa_listening_start", self._on_chat_listening_start)
        AsyncBroker().subscribe("chat_listening_start", self._on_chat_listening_start)
        AsyncBroker().subscribe("chat_user_input", self._on_chat_user_input)
        AsyncBroker().subscribe("chat_done", self._on_chat_done)
        AsyncBroker().subscribe("chat_done_listening", self._on_chat_done_listening)
        AsyncBroker().subscribe("wake_up", self._on_wake_up)

        # Load Faster Whisper model
        self.model = WhisperModel(model_size, device=device, compute_type=compute_type)
        self.log(f"Faster Whisper model '{model_size}' loaded on {device} with {compute_type}.")

        # self.emotion_analyzer = EmotionAnalyzer()

        # Initialize WebRTC VAD
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(0)  # 민감도 설정 (0=낮음, 3=높음)
        
        # 오디오 데이터 버퍼
        self.audio_buffer = []
        self.speech_detected_frames = 0  # 연속 음성 프레임 수

        self.chat_done_flag = False
        self.chat_conected = False

    def _pcm_to_wav(self, pcm_data, sample_rate=16000, num_channels=1, sample_width=2):
        """
        Convert raw PCM data to WAV format and return a BytesIO object.
        """
        wav_buffer = BytesIO()
    
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(num_channels)
            wav_file.setsampwidth(sample_width)  # 2 bytes for 16-bit PCM
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm_data)
        wav_buffer.seek(0)  # Ensure the pointer is at the beginning
        return wav_buffer
    
    def _process_audio_data(self, audio_buffer) -> str:
        """
        Process raw PCM audio data and return the recognized text.
        :param audio_data: PCM audio data (16kHz, 16-bit, mono)
        :return: Recognized text.
        """
        try:
            # Recognize speech using Faster Whisper
            segments, info = self.model.transcribe(audio_buffer,
            task="transcribe",
            beam_size=5,
            temperature=0.0,
            language="ko")
            recognized_text = "".join([segment.text for segment in segments])
            
            return recognized_text.strip()
        except Exception as e:
            self.log(f"Error during recognition: {e}")
            return ""

    def _recognize_routine(self):
        """
        Routine to process microphone input and emit messages.
        """
        with Microphone() as mic:
            self.log("Microphone activated for Whisper recognition.")
            while mic.is_active() and not self._mic_end.is_set():
                if not ChatWindow.use_whisper:
                    self.chat_conected = False
                    return  # 키보드 모드에서는 인식 중지
                try:
                    # Read audio data from microphone (20ms chunks)
                    chunk = mic.read(320)  # 20ms PCM data

                    # Check if speech is detected
                    is_speech = self.vad.is_speech(chunk, sample_rate=16000)

                    if is_speech:
                        # 데이터를 정규화하고 필터링
                        if self.speech_detected_frames == 0:
                            user_input_start_time = get_current_timestamp()

                        audio_data = np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32767.0

                        self.audio_buffer.append((audio_data * 32767).astype(np.int16).tobytes())
                        self.speech_detected_frames += 1
                    else:
                        if self.speech_detected_frames >= 10:
                            self.log("Processing detected speech...")

                            # PCM 데이터를 합치고 WAV로 변환
                            pcm_data = b"".join(self.audio_buffer)

                            # 입력 데이터 길이 검증
                            if len(pcm_data) < 16000:  # 최소 1초 데이터
                                self.log("Insufficient audio data for transcription.")
                                self.audio_buffer = []  # 초기화
                                self.speech_detected_frames = 0
                                continue
                            if not pcm_data or len(pcm_data) == 0:
                                raise ValueError("pcm_data is empty or None")

                            wav_buffer = self._pcm_to_wav(pcm_data, mic.SAMPLE_RATE)

                            # Whisper 모델로 텍스트 변환
                            try:
                                self.log("Whisper transcribe_audio")
                                transcript = self._process_audio_data(wav_buffer)

                                # Emit the same message format as Clova Recognizer
                                if transcript:
                                    if self.TEST_MODE:
                                        print(f"Recognized: {transcript}")  # 터미널 출력
                                    else:
                                        self.chat_conected = False
                                        if self.chat_done_flag :
                                            if "대화하자" in transcript and "친구님" in transcript:
                                                self.log("일어났어요.")
                                                AsyncBroker().emit(("wake_up", None))
                                        else :
                                            user_input_end_time = get_current_timestamp()
                                            
                                            AsyncBroker().emit(("chat_cycle_time", {"content": "WHISPER MODE", "start_time": self.whisper_start_time, "end_time": user_input_end_time}))
                                            AsyncBroker().emit(("chat_user_input", {"content": transcript, "start_time": user_input_start_time, "end_time": user_input_end_time}))
                            except Exception as e:
                                print(f"Whisper processing error: {e}")

                        # 버퍼 및 상태 초기화
                        self.audio_buffer = []
                        self.speech_detected_frames = 0

                except Exception as e:
                    self.log(f"Error in recognition routine: {e}")
                    break

    def _on_chat_listening_start(self, _: AsyncMessageType[None]):
        """
        Start the speech recognition routine when listening starts.
        """
        if self.chat_conected:
            self.log("Already start Whisper recognition.")
            return  
        if not ChatWindow.use_whisper:
            self.log("Whisper disabled (keyboard mode)")
            return
        self.chat_conected = True
        self._mic_end.clear()
        self._recognize_thread = Thread(target=self._recognize_routine)
        self._recognize_thread.start()
        self.whisper_start_time = get_current_timestamp()

    def _on_chat_user_input(self, _: AsyncMessageType[None]):
        """
        Stop recognition when user input is detected.
        """
        self._stop_recognition()

    def _on_chat_done(self, _: AsyncMessageType[None]):
        """
        Stop recognition when chat is done.
        """
        self.log("Whisper Chat Done")
        self._stop_recognition()

    def _stop_recognition(self):
        """
        Stop the recognition process.
        """
        self._mic_end.set()
        self.log("Whisper Mic End Set")
        if self._recognize_thread is not None:
            self._recognize_thread.join()
            self._recognize_thread = None
        self.log("Stopped recognition.")
    
    def _on_chat_done_listening(self, msg: AsyncMessageType):
        self.log("Whisper_친구님 인식 시작")
        self.chat_done_flag = True
        AsyncBroker().emit(("cumpa_listening_start", None))

    def _on_wake_up(self, _: tuple[str, None]):
        self.chat_done_flag = False
        self.log("Whisper_Wake Up")

if __name__ == "__main__":
    print("Starting Whisper Speech Recognition in Standalone Mode...")
    recognizer = FasterWhisperRecognizer()
    recognizer.TEST_MODE = True  # 독립 실행 모드 활성화
    recognizer._recognize_routine()  # 마이크 입력 및 음성 인식 시작