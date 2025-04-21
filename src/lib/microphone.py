import pyaudio

pa = pyaudio.PyAudio() # This instance need to be terminated at the end of the whole program.

class Microphone():
    """
    class for audiostreams

    Attributes:
        stream : pyaudio stream
    """
    SAMPLE_RATE = 16000
    PA_FORMAT = pyaudio.paInt16
    CHUNK_SIZE = 1600

    def __enter__(self) -> "Microphone":
        self.open()
        return self
    
    def __exit__(self, type, value, traceback):
        self.close()

    def is_active(self) -> bool:
        return self.stream is not None and self.stream.is_active()

    def close(self) -> None:
        self.stream.close()

    def open(self) -> None:
        """
        output_device_index selects the speaker index.
        """
        self.stream = pa.open(channels=1,
                            format=self.PA_FORMAT,
                            rate=self.SAMPLE_RATE, 
                            frames_per_buffer=self.CHUNK_SIZE,
                            input=True,
                            output_device_index=0,
                            output = False)
    
    def read(self, num_frames: int):
        """
        Read audio data from the stream.
        """
        return self.stream.read(num_frames, exception_on_overflow=False)