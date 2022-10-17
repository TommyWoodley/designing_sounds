import numpy as np
import pyaudio
from src.wave_model.wave_model import normalize_sound


class WaveSound:
    def __init__(self, sample_rate, time):
        self.is_playing = False
        self.sample_rate = sample_rate
        self.time = time

        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format=pyaudio.paFloat32, channels=1, rate=self.sample_rate, output=True, stream_callback=self.callback, frames_per_buffer=int(self.sample_rate*time))
        self.sound = np.array([]).astype(np.float32).tostring()

    def callback(self, in_data, frame_count, time_info, flag):
        return self.sound, pyaudio.paContinue

    def update_sound(self, sound:  np.ndarray) -> None:
        points = np.copy(normalize_sound(sound))
        self.sound = points.tostring()

    def press_button_play(self) -> None:
        if not self.is_playing:
            self.is_playing = True
            self.stream.start_stream()

        else:
            self.is_playing = False
            self.stream.stop_stream()

    def loop_play(self) -> None:
        while self.is_playing:
            x = self.sound.play()
            x.wait_done()
