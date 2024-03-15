import numpy as np
import wave
from scipy.io import wavfile
from scipy import signal
from functools import cache

SAMPLE_RATE_TABLE = [8000,9600,11000,12000,16000,19200,22100,24000,32000,38400,44100,48000]

class SignalProcesses(object):
    def __init__(self, settings, logger):
        self.__settings = settings
        self.__logger = logger
        self.__hop_len = int(settings.tap * settings.overlap_rate)
        self.__window = signal.get_window(settings.window,settings.tap)
        self.logger.app.debug("instantized")

    def wav_load(self, wav_path) -> np.ndarray:
        try:
            with wave.open(wav_path, 'rb') as wv:
                n_ch = wv.getnchannels()
                fs = wv.getframerate()
            if n_ch != 2:
                msg = f"{wav_path}:ステレオ信号ではありません[channels={n_ch}]"
                raise ValueError(msg)
            elif not fs in SAMPLE_RATE_TABLE:
                msg = f"{wav_path}:wavファイルのサンプリング周波数が非対応です[fs={fs}]"
                raise ValueError(msg)
        except Exception as e:
            msg = f"waveファイルの読み込み失敗[{e}]"
            self.logger.app.error(msg)
            return False
        _, data = wavfile.read(wav_path)
        self.logger.app.debug(f"{wav_path}:読み込み成功")
        return fs, data

    @cache
    def make_oct_mask(self, ceter_freq, fs) -> np.ndarray:
        try:
            oct_freq_l = ceter_freq / 2**(1 / 2)
            oct_freq_h = ceter_freq * 2**(1 / 2)
            fft_f = np.fft.rfftfreq(self.settings.tap, 1 / fs)
            oct_freq_mask = np.array([(fft_f >= oct_freq_l) & (fft_f < oct_freq_h)])
            oct_freq_mask = oct_freq_mask.reshape([-1,1])
        except Exception as e:
            msg = f"オクターブバンドフィルタの作成に失敗[{e}]"
            self.logger.app.error(msg)
            raise ValueError(msg)
        return oct_freq_mask

    def cal_CPB_percentile_level(self, signal, oct_mask, fs, percentile):
        frame_num = int(np.floor((signal.shape[0] - self.settings.tap) / self.hop_len)) + 1
        if frame_num < 1:
            msg = f"失敗:データ長がFFT点数{self.settings.tap}に満たない"
            raise ValueError(msg)
        if signal.shape[0] < self.settings.mean_time * self.settings.tap:
            msg = f"失敗:データ長が指定の平均化時間{self.settings.mean_time}秒に満たない"
            raise ValueError(msg)
        f=[]
        L=[]
        rfft = np.fft.rfft
        hop_len_sec = self.hop_len * fs
        mean_time = hop_len_sec
        for i in range(frame_num):
            frame = self.window * signal[(self.hop_len * i):(self.settings.tap + (self.hop_len * i))]
            f.append(rfft(frame, axis=0))
            mean_time += hop_len_sec
            if mean_time >= self.settings.mean_time:
                S = (np.mean(np.abs(np.stack(f, axis=0)), axis = 0))
                L.append(10 * np.log10(np.sum(S[oct_mask[:,0]], axis = 0)))
                f = []
                mean_time = hop_len_sec
        return np.percentile(L, percentile)

    # def cal_mean_level(self, signal, detection_width):
    #     rfft = np.fft.rfft
    #     frame_num = int(np.floor((signal.shape[0] - self.tap) / self.hop_len)) + 1
    #     if frame_num < 1:
    #         msg = f"Error:信号長がFFT点数{self.tap}に満たないのでダメです"
    #         self.logger.app.error(msg)
    #         return False
    #     hop_len_count = self.overlap_rate * detection_width
    #     f = []
    #     result = []
    #     count = hop_len_count
    #     for i in range(frame_num):
    #         frame = self.window * signal[(self.hop_len * i):(self.tap + (self.hop_len * i))]
    #         f.append(rfft(frame, axis=0))
    #         count += hop_len_count
    #         if count >= detection_width:
    #             S = (np.mean(np.abs(np.stack(f, axis=0)), axis = 0))
    #             result.append(10 * np.log10(np.sum(S, axis = 0)))
    #             f = []
    #             count = 0

    #     return result

    @property
    def logger(self):
        return self.__logger

    @property
    def settings(self):
        return self.__settings

    @property
    def hop_len(self):
        return self.__hop_len

    @property
    def window(self):
        return self.__window