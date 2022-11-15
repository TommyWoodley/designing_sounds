import threading
import typing

import numpy as np

from math import *


class PowerSpectrum:
    def __init__(self, max_harmonics: int, max_samples_per_harmonic: int):
        self.max_samples_per_harmonic = max_samples_per_harmonic
        self.harmonics = np.zeros((max_harmonics, self.max_samples_per_harmonic), dtype=np.float32)
        self.functions = {'sqrt': sqrt, 'pow': pow, 'log': log, 'log2': log2, 'log10': log10, 'cos': cos, 'sin': sin,
                          'tan': tan, 'ceil': ceil, 'abs': fabs, 'factorial': factorial}

    def update_harmonic(self, harmonic_index, mean: int, std: float, num_harmonic_samples: int,
                        num_harmonics: int, decay_function: str) -> None:
        num_samples = 0
        freqs = np.array([])

        for x in range(num_harmonics):
            self.functions['x'] = x + 1
            decay_factor = eval(decay_function, {'__builtins__': None}, self.functions) if type(decay_function) == str else 1
            sample_size = int(num_harmonic_samples * decay_factor)
            num_samples += sample_size
            freqs = np.append(freqs, np.random.randn(sample_size) * std + mean * pow(2, x))

        self.harmonics[harmonic_index] = np.zeros(max(self.max_samples_per_harmonic, num_samples))
        self.harmonics[harmonic_index, :num_samples] = freqs


class SoundModel:
    def __init__(self, max_harmonics: int, max_samples_per_harmonic: int, max_freq: int):
        self.max_freq = max_freq
        self.max_harmonics = max_harmonics
        self.max_samples_per_harmonic = max_samples_per_harmonic
        self.amps = np.asarray(np.random.randn(self.max_samples_per_harmonic * self.max_harmonics), dtype=np.float32)
        self.phases = None
        self.power_spectrum = PowerSpectrum(self.max_harmonics, self.max_samples_per_harmonic)
        self.samples_per_harmonic = np.zeros(self.max_harmonics)
        self.lock = threading.Lock()

    def get_power_spectrum_histogram(self, harmonic_index: int,
                                     _num_bins: int) -> typing.List[typing.Tuple[float, float]]:
        with self.lock:
            freqs = self.power_spectrum.harmonics[harmonic_index]
            freqs = freqs[np.nonzero(freqs)]
            histogram, bin_edges = np.histogram(freqs, self.max_freq // 2, range=(0.1, 1000))
        return list(zip(bin_edges, histogram))

    def get_sum_all_power_spectrum_histogram(self) -> typing.List[typing.Tuple[float, float]]:
        with self.lock:
            freqs = self.power_spectrum.harmonics.flatten()
            freqs = freqs[np.nonzero(freqs)]
            histogram, bin_edges = np.histogram(freqs, self.max_freq // 2, range=(0.1, 1000))
        return list(zip(bin_edges, histogram))

    def interpolate_points(self, points: typing.List[typing.Tuple[float, float]]):
        if points:
            x, y = (np.array([i for i, _ in points]), np.array([j for _, j in points]))
            with self.lock:
                self.amps, _, _, _ = np.linalg.lstsq(self.calculate_sins(x),
                                                     y * self.max_harmonics * self.max_samples_per_harmonic, rcond=None)
                self.amps = np.asarray(self.amps, dtype=np.float32)
        else:
            self.amps = np.asarray(np.random.randn(self.max_samples_per_harmonic * self.max_harmonics),
                                   dtype=np.float32)

    def update_power_spectrum(self, harmonic_index: int, mean: int, std: float, num_harmonic_samples: int,
                              num_harmonics: int, decay_function: str) -> None:
        with self.lock:
            self.power_spectrum.update_harmonic(harmonic_index, mean, std, num_harmonic_samples, num_harmonics,
                                                decay_function)
            self.samples_per_harmonic[harmonic_index] = num_harmonic_samples
            self.phases = np.asarray(np.random.uniform(0, self.max_freq,
                                                       self.max_harmonics * self.max_samples_per_harmonic),
                                     dtype=np.float32)

    def calculate_sins(self, x):
        freqs = self.power_spectrum.harmonics.flatten()
        sins = np.sin((x[:, None]) * 2 * np.pi * freqs)
        return sins

    def model_sound(self, sample_rate: int, chunk_duration: float, start_time: float) -> np.ndarray:
        x = np.linspace(start_time, start_time + chunk_duration, int(chunk_duration * sample_rate), endpoint=False,
                        dtype=np.float32)

        with self.lock:
            sound = (self.calculate_sins(x) @ self.amps) / (self.max_harmonics * self.max_samples_per_harmonic)
        sound[sound > 1] = 1
        sound[sound < -1] = -1
        return sound

    def model_sound_graph(self, sample_rate: int, chunk_duration: float, start_time: float) -> np.ndarray:
        x = np.linspace(start_time, start_time + chunk_duration, int(chunk_duration * sample_rate), endpoint=False,
                        dtype=np.float32)

        with self.lock:
            sound = (self.calculate_sins(x) @ self.amps) / (self.max_harmonics * self.max_samples_per_harmonic)

        return sound
