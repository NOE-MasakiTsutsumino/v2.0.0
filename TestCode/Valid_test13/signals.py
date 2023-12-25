import os
import numpy as np
import wave
from scipy.io import wavfile

SAMPLE_RATE_TABLE = [8000,9600,11000,12000,16000,19200,22100,24000,32000,38400,44100,48000]

class SignalProcesses(object):

    def __init__(self, settings, logger):

        self.logger = logger

        self.wav_directory = settings.wav_directory
        self.tap = settings.tap
        self.mean_time = settings.mean_time

        # fftのoverlapの割合 % から移fft一回毎に移動するサンプルサイズを求める
        self.overlap_rate = settings.overlap_rate
        self.hop_len = int(self.tap * self.overlap_rate)

        # fftの窓関数作成
        self.window = settings.window
        window_labels = ["hanning", "hamming", "blackman"]
        assert self.window in window_labels, f"窓関数名が不正です: {self.window}"
        label = "np." + self.window + "(self.tap)"
        self.window_func = eval(label)

    def wav_load(self, wav_path) -> np.ndarray:

        if not os.path.exists(wav_path):
            raise ValueError(f"WAVEファイルが見つかりません:{wav_path}")

        with wave.open(wav_path, 'rb') as wv:
            n_ch = wv.getnchannels()
            fs = wv.getframerate()
        if n_ch != 2:
            raise ValueError(f"ステレオ信号ではありません: {wav_path},channel = {n_ch}")
        elif not fs in SAMPLE_RATE_TABLE:
            raise ValueError(f"非対応のサンプリング周波数です: {wav_path},fs = {fs}Hz")

        # 対象ファイルの読み込み
        _, data = wavfile.read(wav_path)

        self.logger.app_logger.debug(f"wave_load:{wav_path}")

        return fs, data

    def make_oct_mask(self, ceter_freq, fs) -> np.ndarray:

        oct_freq_l = ceter_freq / 2**(1 / 2)
        oct_freq_h = ceter_freq * 2**(1 / 2)

        fft_f = np.fft.rfftfreq(self.tap, 1 / fs)
        oct_freq_mask = np.array([(fft_f >= oct_freq_l) & (fft_f < oct_freq_h)])

        return oct_freq_mask.reshape([-1,1])

    def cal_CPB_mean_level(self, signal, oct_mask):

        frame_num = int(np.floor((signal.shape[0] - self.tap) / self.hop_len)) + 1

        if frame_num < 1:
            msg = f"Error:信号長がFFT点数{self.tap}に満たないのでダメです"
            self.logger.app_logger.error(msg)
            return False

        rfft = np.fft.rfft
        f = []
        for i in range(frame_num):
            frame = self.window_func * signal[(self.hop_len * i):(self.tap + (self.hop_len * i))]
            f.append(rfft(frame, axis=0))

        S = (np.mean(np.abs(np.stack(f, axis=0)), axis = 0))
        result = 10 * np.log10(np.sum(S[oct_mask[:,0]], axis = 0))

        return result

    def cal_CPB_percentile_level(self, signal, oct_mask, fs, percentile):

        frame_num = int(np.floor((signal.shape[0] - self.tap) / self.hop_len)) + 1

        if frame_num < 1:
            msg = f"Error:信号長がFFT点数{self.tap}に満たないのでダメです"
            self.logger.app_logger.error(msg)
            return False

        if signal.shape[0] < self.mean_time * self.tap:
            msg = f"Error:信号長が指定の平均化時間{self.mean_time}秒に満たないのでダメです"
            self.logger.app_logger.error(msg)
            return False

        rfft = np.fft.rfft
        hop_len_sec = self.hop_len * fs

        f = []
        L = []
        mean_time = hop_len_sec
        for i in range(frame_num):
            frame = self.window_func * signal[(self.hop_len * i):(self.tap + (self.hop_len * i))]
            f.append(rfft(frame, axis=0))
            mean_time += hop_len_sec

            if mean_time >= self.mean_time:
                S = (np.mean(np.abs(np.stack(f, axis=0)), axis = 0))
                L.append(10 * np.log10(np.sum(S[oct_mask[:,0]], axis = 0)))
                f = []
                mean_time = hop_len_sec

        result = np.percentile(L, percentile)

        return result
