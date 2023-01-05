import typing

import numpy as np

from kivy.core.window import Window
from kivy.lang import Builder

from kivy.properties import (StringProperty, ObjectProperty)

from kivy_garden.graph import LinePlot
from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.list import OneLineAvatarIconListItem, IRightBodyTouch
from kivymd.uix.menu import MDDropdownMenu

from src.wave_controller.instruments import PianoMIDI
from src.wave_controller.wave_graph import WaveformGraph
from src.wave_controller.wave_sound import WaveSound
from src.wave_model.wave_model import SoundModel
from src.wave_view import style
import src.wave_controller.power

Builder.load_file('src/wave_view/power.kv')
Builder.load_file('src/wave_view/wave.kv')

SINE_WAVE = 0
SQUARE_WAVE = 1
TRIANGLE_WAVE = 2
SAWTOOTH_WAVE = 3


class RightContentCls(IRightBodyTouch, MDBoxLayout):
    icon = StringProperty()
    text = StringProperty()


class Item(OneLineAvatarIconListItem):
    left_icon = StringProperty()
    right_icon = StringProperty()
    right_text = StringProperty()


class RootWave(MDBoxLayout):
    ps_controller = ObjectProperty(None)
    sample_rate = 16000
    graph_sample_rate = 8000
    waveform_duration = 1
    chunk_duration = 0.1

    def __init__(self, **kwargs: typing.Any):
        super().__init__(**kwargs)
        self.is_showing = False
        self.file_manager = None
        self.loaded_file = None

        self.sound_model = SoundModel(self.ps_controller.max_harmonics_per_spectrum)

        self.wave_sound = WaveSound(self.sample_rate, self.chunk_duration, self.sound_model)

        # Button bindings
        self.play.bind(on_press=self.press_button_play)
        self.back.bind(on_press=self.press_button_back)
        self.eraser_mode.bind(on_press=self.press_button_eraser)
        self.clear.bind(on_press=self.press_button_clear)
        self.resample.bind(on_press=self.press_button_resample)
        self.connect_button.bind(on_press=self.press_button_connect)

        # Wave Graphs
        border_color = [0, 0, 0, 1]
        self.waveform_graph = WaveformGraph(update_waveform=self.update_waveform,
                                            update_waveform_graph=self.update_waveform_graph, size_hint=(1, 1),
                                            border_color=border_color,
                                            xmin=0, xmax=self.waveform_duration, ymin=-1.0, ymax=1.0, padding=10,
                                            draw_border=True, x_grid_label=True, y_grid_label=True, xlabel='Time',
                                            ylabel='Amplitude', precision="%.5g", x_grid=True, y_grid=True,
                                            y_ticks_major=0.25, label_options=dict(color=(0, 0, 0, 1)))

        self.ids.modulation.add_widget(self.waveform_graph)

        plot_color = style.cyber_grape

        self.wave_plot = LinePlot(color=plot_color, line_width=1)
        self.load_sound_plot = LinePlot(color=style.red, line_width=1)

        self.waveform_graph.add_plot(self.wave_plot)
        self.waveform_graph.add_plot(self.load_sound_plot)

        self.ps_controller.sound_model = self.sound_model
        self.ps_controller.update_waveform = self.update_waveform
        self.ps_controller.waveform_graph = self.waveform_graph

        choose_wave_menu_items = [
            {
                "text": "Sine Wave",
                "right_text": "",
                "right_icon": "",
                "left_icon": "sine-wave",
                "viewclass": "Item",
                "on_release": lambda x=True: self.preset_waves(SINE_WAVE),
            },
            {
                "text": "Square Wave",
                "right_text": "",
                "right_icon": "",
                "left_icon": "square-wave",
                "viewclass": "Item",
                "on_release": lambda x=True: self.preset_waves(SQUARE_WAVE),
            },
            {
                "text": "Triangle Wave",
                "right_text": "",
                "right_icon": "",
                "left_icon": "triangle-wave",
                "viewclass": "Item",
                "on_release": lambda x=True: self.preset_waves(TRIANGLE_WAVE),
            },
            {
                "text": "Sawtooth Wave",
                "right_text": "",
                "right_icon": "",
                "left_icon": "sawtooth-wave",
                "viewclass": "Item",
                "on_release": lambda x=True: self.preset_waves(SAWTOOTH_WAVE),
            }
        ]
        self.choose_wave_menu = MDDropdownMenu(
            caller=self.preset,
            items=choose_wave_menu_items,
            width_mult=4,
        )
        self.piano = PianoMIDI()

        Window.bind(on_request_close=self.shutdown_audio)

    def update_waveform(self, update_noise=False) -> None:
        self.sound_model.interpolate_points(self.waveform_graph.get_selected_points(), update_noise)
        self.update_waveform_graph()

    def update_loaded_sound_graph(self) -> None:
        x_min = self.waveform_graph.xmin
        x_max = self.waveform_graph.xmax
        sample_rate, data = self.loaded_file
        start_index = int(self.sample_rate * x_min)
        finish_index = int(self.sample_rate * x_max)
        self.load_sound_plot.points = list(
            zip(np.linspace(x_min, x_max, finish_index - start_index), data[start_index:finish_index]))

    def update_waveform_graph(self) -> None:
        x_min = self.waveform_graph.xmin
        x_max = self.waveform_graph.xmax
        points = self.sound_model.model_sound(self.graph_sample_rate / (x_max - x_min), x_max - x_min, x_min)
        self.wave_plot.points = list(zip(np.linspace(x_min, x_max, points.size), points))
        if self.loaded_file and self.is_showing:
            self.update_loaded_sound_graph()

    def press_button_play(self, _: typing.Any) -> None:
        if self.wave_sound.is_playing():
            self.wave_sound.pause_audio()
            self.play.icon = "play"
            self.play.md_bg_color = style.blue_violet
        else:
            self.play.icon = "pause"
            self.play.md_bg_color = style.dark_sky_blue
            self.wave_sound.play_audio()

    def press_button_connect(self, _: typing.Any) -> None:
        if self.piano.begin(self.ps_controller.power_spectrum_from_freqs):  # Has successfully started
            self.connect_button.text = 'Disconnect MIDI Piano '
            self.connect_button.md_bg_color = style.dark_sky_blue
        else:  # Was already running so disconnected
            self.connect_button.text = '  Connect MIDI Piano  '
            self.connect_button.md_bg_color = style.blue_violet

    def press_button_show_loaded_sound(self, _: typing.Any) -> None:
        if self.loaded_file:
            if self.is_showing:
                # Hide the graphs
                self.is_showing = False
                self.show_loaded.icon = "cellphone-sound"
                self.show_loaded.text = "Show Loaded Sound"
                self.load_sound_plot.points = []
                self.old_sound_power_plot_points = self.ps_controller.sound_power_plot.points
                self.ps_controller.sound_power_plot.points = []
                self.show_loaded.md_bg_color = style.blue_violet
            else:
                self.is_showing = True
                self.show_loaded.icon = "file-hidden"
                self.show_loaded.text = "Hide Loaded Sound"
                _, data = self.loaded_file
                self.update_loaded_sound_graph()

                self.ps_controller.sound_power_plot.points = self.old_sound_power_plot_points
                self.show_loaded.md_bg_color = style.dark_sky_blue

    def press_button_back(self, _: typing.Any) -> None:
        self.wave_sound.sound_changed()

    def press_button_eraser(self, _: typing.Any) -> None:
        if self.waveform_graph.is_eraser_mode():
            # Eraser Mode -> Draw Mode
            self.waveform_graph.set_draw_mode()
            self.eraser_mode.icon = "eraser"
            self.eraser_mode.md_bg_color = style.blue_violet
        else:
            # Draw Mode -> Eraser Mode
            self.waveform_graph.set_eraser_mode()
            self.eraser_mode.icon = "pen"
            self.eraser_mode.md_bg_color = style.dark_sky_blue

    def press_button_clear(self, _: typing.Any) -> None:
        self.waveform_graph.clear_selected_points()
        self.update_waveform()

    def press_button_resample(self, _: typing.Any) -> None:
        self.sound_model.update_prior()
        self.update_waveform()

    def preset_waves(self, x: int):
        num_points = 100

        def sin_wave(x, period):
            amp_scale = 0.75
            scale = (2 * np.pi)
            return amp_scale * np.sin((scale / period) * x)

        def square_wave(x, period):
            square_scale = 0.75
            return -square_scale if x < (period / 2) else square_scale

        def triangle_wave(x, period):
            scale = 3
            slope = (scale / period)
            scale_factor = scale / 4
            if 0 <= x < period / 4:
                return slope * x
            if period / 4 <= x < 3 * period / 4:
                return scale_factor * 2 - slope * x
            return slope * x - scale_factor * 4

        def sawtooth_wave(x, period):
            return 3 / 2 / period * x - 3 / 4

        waves = [sin_wave, square_wave, triangle_wave, sawtooth_wave]
        self.sound_model.interpolate_points(
            self.waveform_graph.get_preset_points(waves[x], num_points, waves[x] == square_wave))
        self.ps_controller.update_power_spectrum()
        self.wave_sound.sound_changed()

    def shutdown_audio(self, _) -> bool:
        self.wave_sound.shutdown()
        self.piano.shutdown()
        return False

    def open_choose_wave_menu(self) -> None:
        self.choose_wave_menu.open()


class WaveApp(MDApp):
    def build(self) -> RootWave:
        return RootWave()
