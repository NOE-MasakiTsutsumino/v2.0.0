import os
import numpy as np
import wave
from scipy.io import wavfile
from pathlib import Path

class SignalProcesses(object):

    def __init__(self, settings, logger):

        self.logger = logger

        # WAVEファイル場所
        self.wave_dir = Path(settings.wave_dir)

        # WAVEファイルのサンプリング周波数 このサンプリング周波数ではないWAVEファイルを読み込むとエラーを吐く
        self.wave_samplelate = int(settings.fft_parameters["wave_samplelate"])

        # fft点数
        self.fft_n = int(settings.fft_parameters["fft_n"])

        # CPBフィルタの周波数軸作成
        self.fft_f = np.fft.rfftfreq(self.fft_n, 1 / self.wave_samplelate)

        # fftのoverlapの割合 % から移fft一回毎に移動するサンプルサイズを求める
        self.overlap_percent = float(settings.fft_parameters["overlap_percent"])

        self.hop_len = int(self.fft_n * self.overlap_percent / 100.0)

        # fftの窓関数作成
        #! numpyでなくscipyを使って使用できる窓関数の種類を増やす
        self.window = str(settings.fft_parameters["window"])
        window_labels = ["hanning", "hamming", "blackman"]
        assert self.window in window_labels, f"窓関数名が不正です: {self.window}"
        label = "np." + self.window + "(self.fft_n)"
        self.window_func = eval(label)

        # バンドパスフィルタ作成
        freqs = settings.common["target_frequency"]
        self.oct_freq_mask={}
        for freq in freqs:
            self.oct_freq_mask[str(freq)] = self.make_oct_mask(freq)

    def wav_load(self, wav_path) -> np.ndarray:
        """2chのWAVEファイルを読み込んで信号を返す

        Args:
            wav_path (Path): wavefileのfullpath
            slm_ch (int): 騒音計信号のindex 基本SubMicが0,SLMが1

        Raises:
            ValueError: openしたwaveのch数が2でなければならない
            ValueError: openしたwaveのsamplerateは12000でなければならない
        Returns:
            numpy array: stereo signalのsample値
        """

        if not os.path.exists(wav_path):
            raise ValueError("WAVEファイルが見つかりません:{}".format(wav_path))

        with wave.open(wav_path, 'rb') as wv:
            n_ch = wv.getnchannels()
            fs = wv.getframerate()
        if n_ch != 2:
            raise ValueError(f"ステレオ信号ではありません: {wav_path}")
        elif fs != self.wave_samplelate:
            raise ValueError(f"サンプリング周波数が対象外です: {wav_path}")

        # 対象ファイルの読み込み
        _, data = wavfile.read(wav_path)

        self.logger.app.debug(f"wave_load:{wav_path}")

        return data

    def make_oct_mask(self, ceter_freq) -> np.ndarray:
        """
        オクターブバンドフィルタ作成
        """

        oct_freq_l = ceter_freq / 2**(1 / 2)
        oct_freq_h = ceter_freq * 2**(1 / 2)
        oct_freq_mask = np.array([(self.fft_f >= oct_freq_l) & (self.fft_f < oct_freq_h)])

        return oct_freq_mask.reshape([-1,1])

    def cal_CPB_mean_level(self, signal, oct_freq_mask):

        frame_num = int(np.floor((signal.shape[0] - self.fft_n) / self.hop_len)) + 1

        if frame_num < 1:
            msg = f"Error:信号長がFFT点数{self.fft_n}に満たないのでダメです"
            self.logger.app.error(msg)
            return False

        rfft = np.fft.rfft

        f = []
        for i in range(frame_num):
            frame = self.window_func * signal[(self.hop_len * i):(self.fft_n + (self.hop_len * i))]
            f.append(rfft(frame, axis=0))

        S = (np.mean(np.abs(np.stack(f, axis=0)), axis = 0))
        result = 10 * np.log10(np.sum(S[oct_freq_mask[:,0]], axis = 0))

        return result

    def cal_CPB_percentile_level(self, signal, oct_freq_mask, percent):

        if not (percent <= 100 and percent > 0):
            msg = f"percentは0から100の数値で指定して下さい:{percent}"
            self.logger.app.critical(msg)
            raise Exception(msg)

        frame_num = int(np.floor((signal.shape[0] - self.fft_n) / self.hop_len)) + 1

        if frame_num < 1:
            msg = f"Error:信号長がFFT点数{self.fft_n}に満たないのでダメです"
            self.logger.app.error(msg)
            return False

        rfft = np.fft.rfft

        L = []
        for i in range(frame_num):
            frame = self.window_func * signal[(self.hop_len * i):(self.fft_n + (self.hop_len * i))]
            S = rfft(frame, axis=0)
            L.append(10 * np.log10(np.sum(np.abs(S[oct_freq_mask[:,0]]), axis = 0)))

        result = np.percentile(L, percent)

        return result