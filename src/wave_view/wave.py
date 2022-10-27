import typing

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy_garden.graph import LinePlot, Graph, BarPlot

from src.wave_model.wave_model import SoundModel
from src.wave_view.wave_sound import WaveSound
from src.wave_view.wave_graph import WaveformGraph
import numpy as np


class RootWave(BoxLayout):
    sample_rate = 44100
    graph_sample_rate = 2500
    power_spectrum_graph_samples = 10
    waveform_duration = 1
    chunk_duration = 0.1

    max_harmonics = 10
    num_harmonics = 0
    current_harmonic_index = 0

    def __init__(self, **kwargs: typing.Any):
        super(RootWave, self).__init__(**kwargs)
        self.max_samples_per_harmonic = int(self.harmonic_samples.max)

        self.change_harmonic = False
        self.sound_model = SoundModel(self.max_harmonics, self.max_samples_per_harmonic, int(self.mean.max))
        self.wave_sound = WaveSound(self.sample_rate, self.waveform_duration, self.chunk_duration, self.sound_model)

        self.play.bind(on_press=self.press_button_play)
        self.clear.bind(on_press=self.press_button_clear)
        self.add.bind(on_press=self.press_button_add)

        border_color = [0, 1, 1, 1]

        self.waveform_graph = WaveformGraph(update=self.update_waveform,
                                            border_color=border_color,
                                            xmin=0, xmax=self.waveform_duration,
                                            ymin=-1.0, ymax=1.0,
                                            draw_border=True, padding=0, x_grid_label=True, y_grid_label=False)
        self.power_spectrum_graph = Graph(border_color=border_color,
                                          xmin=0, xmax=self.mean.max,
                                          ymin=0, ymax=self.harmonic_samples.max,
                                          draw_border=True)

        self.ids.modulation.add_widget(self.waveform_graph)
        self.ids.power_spectrum.add_widget(self.power_spectrum_graph)

        plot_color = [1, 1, 0, 1]
        self.wave_plot = LinePlot(color=plot_color, line_width=1)
        self.power_plot = BarPlot(color=plot_color)

        self.waveform_graph.add_plot(self.wave_plot)
        self.power_spectrum_graph.add_plot(self.power_plot)

        self.power_buttons = []
        self.harmonic_list = np.zeros((self.max_harmonics, 3))
        self.press_button_add(None)

    def update_power_spectrum(self, mean: float, sd: float, num_samples: float) -> None:
        if not self.change_harmonic:
            self.sound_model.update_power_spectrum(self.current_harmonic_index, mean, sd, int(num_samples))
            self.update_waveform()
        self.power_plot.points = self.sound_model.get_normal_distribution_points(self.current_harmonic_index, self.power_spectrum_graph_samples)
        self.change_harmonic = False

    def update_waveform(self) -> None:
        inputted_points = self.waveform_graph.get_selected_points()
        self.sound_model.interpolate_points(inputted_points)
        points = self.sound_model.model_sound(self.graph_sample_rate, self.waveform_duration, 0)
        self.wave_plot.points = list(zip(np.linspace(0, self.waveform_duration, points.size), points))

    def press_button_play(self, instance: typing.Any) -> None:
        self.wave_sound.press_button_play()

    def press_button_clear(self, instance: typing.Any) -> None:
        self.waveform_graph.clear_selected_points()
        self.update_waveform()

    def press_button_add(self, instance: typing.Any) -> None:
        if self.num_harmonics < self.max_harmonics:
            self.add_power_spectrum_button()
            self.update_power_spectrum(self.mean.value, self.sd.value, self.harmonic_samples.value)

    def press_button_display_power_spectrum(self, instance: typing.Any):
        self.change_harmonic = True
        self.harmonic_list[self.current_harmonic_index] = np.array([self.mean.value, self.sd.value, self.harmonic_samples.value])
        harmonic_index = int(instance.text) - 1
        self.current_harmonic_index = harmonic_index
        mean, sd, num_samples = self.harmonic_list[harmonic_index]
        self.mean.value = int(mean)
        self.sd.value = float(sd)
        self.harmonic_samples.value = int(num_samples)
        # Changing mean, sd and harmonic_samples will automatically call self.update_power_spectrum

    def add_power_spectrum_button(self) -> None:
        self.num_harmonics += 1
        button = Button(text=str(self.num_harmonics), size_hint=(0.1, 1))
        button.bind(on_press=self.press_button_display_power_spectrum)
        self.power_buttons.append(button)
        self.ids.power_spectrum_buttons.add_widget(button)
        self.harmonic_list[self.num_harmonics - 1] = np.array([self.mean.max // 2, 1, self.harmonic_samples.max // 2])


class WaveApp(App):
    def build(self) -> RootWave:
        return RootWave()
