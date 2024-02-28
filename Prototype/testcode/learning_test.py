from datetime import datetime, timedelta
import os
import glob
import numpy as np
import wave
from scipy.io import wavfile
from scipy import signal as sg
from scipy import stats
from functools import cache
from scipy.stats import kurtosis, skew

# テストコード用関数たち

def get_event_time(stid, wav_directory, st_time, next=False):

    if next:
        st_time = (st_time + timedelta(days = 1)).replace(hour=0, minute=0, second=0)

    if st_time.date() >= datetime.now().date() and not next:
        return False

    target_dir = os.path.join(wav_directory, st_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'))

    if os.path.isdir(target_dir):
        wav_list = glob.glob(os.path.join(target_dir,'**','*.WAV'), recursive=True)
    else:
        return get_event_time(stid, wav_directory, st_time, next=True)

    if wav_list == []:
        return get_event_time(stid, wav_directory, st_time, next=True)

    day_event_time_list = []
    for file in wav_list:
        fname = os.path.splitext(os.path.basename(file))[0]
        day_event_time_list.append(datetime.strptime(fname, '%y%m%d%H%M%S'))
    wav_list.clear()

    day_event_time_list = sorted(day_event_time_list,reverse=False)

    for event_time in day_event_time_list:
        if event_time >= st_time:
            path = os.path.join(wav_directory, event_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'),
                                datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
            return event_time, path

    return get_event_time(stid, wav_directory, st_time, next=True)

def wav_load(wav_path) -> np.ndarray:

    try:
        with wave.open(wav_path, 'rb') as wv:
            n_ch = wv.getnchannels()
            fs = wv.getframerate()
        if n_ch != 2:
            msg = f"{wav_path}:ステレオ信号ではありません[channels={n_ch}]"
            raise ValueError(msg)
    except Exception as e:
        msg = f"waveファイルの読み込み失敗[{e}]"
        return False
    _, data = wavfile.read(wav_path)
    return fs, data

def make_oct_masks(ceter_freqs: list , tap: int, fs: int) -> np.ndarray:
    oct_freq_masks = {}
    for freq in ceter_freqs:
        try:
            oct_freq_l = freq / 2**(1 / 2)
            oct_freq_h = freq * 2**(1 / 2)
            fft_f = np.fft.rfftfreq(tap, 1 / fs)
            oct_freq_masks[str(freq)] = np.array([(fft_f >= oct_freq_l) & (fft_f < oct_freq_h)]).reshape([-1,1])
        except Exception as e:
            msg = f"オクターブバンドフィルタの作成に失敗{e}"
            raise Exception(msg)

    return oct_freq_masks

def detect_diff_data(signal, tap, oct_freq_masks, fs, mean_time, percentile):
    diff = lambda x, y : x - y
    window = sg.get_window("hamming",tap)

    sub_data = signal[:,0]
    slm_data = signal[:,1]
    sub_peak_lv, _ = cal_CPB_percentile_values(sub_data, oct_freq_masks, tap, mean_time, window, fs, percentile)
    slm_peak_lv, _ = cal_CPB_percentile_values(slm_data, oct_freq_masks, tap, mean_time, window, fs, percentile)

    # import matplotlib.pyplot as plt
    # fig = plt.figure(figsize=(15, 3))
    # height = sorted(level["1000"])
    # plt.bar(range(len(level["1000"])),level["1000"],color = "orange")
    # plt.hlines(sub_peak_lv[2], 0, len(level["1000"]), "blue", linestyles='dashed')
    # plt.ylabel("level[dB]")
    # plt.xlabel("sample")
    # plt.ylim([30,50])
    # plt.show()

    return list(map(diff, slm_peak_lv, sub_peak_lv))

def cal_CPB_percentile_values(signal, oct_freq_masks, tap, mean_time_sec, window, fs, percentile):

    frame_num = int(np.floor((signal.shape[0]/tap)))
    if frame_num < 1:
        msg = f"失敗:データ長がFFT点数{tap}に満たない"
        raise ValueError(msg)

    if signal.shape[0] < mean_time_sec * tap:
        msg = f"失敗:データ長が指定の平均化時間{mean_time_sec}秒に満たない"
        raise ValueError(msg)

    rfft = np.fft.rfft
    frame_sec = tap / fs
    level = {f'{freq}': list() for freq in oct_freq_masks.keys()}

    fourier_spectrum=[]
    mean_time_count = 0
    for i in range(frame_num):
        frame = window * signal[(tap*i):(tap+(tap*i))]
        fourier_spectrum.append(rfft(frame,axis=0))
        mean_time_count += frame_sec
        if mean_time_count + frame_sec >= mean_time_sec:
            power = np.mean(np.abs(np.stack(fourier_spectrum, axis=0)),axis=0)
            for freq in oct_freq_masks.keys():
                level[freq].append(10*np.log10(np.sum(power[oct_freq_masks[freq][:,0]],axis=0)))
            fourier_spectrum.clear()
            mean_time_count = 0
    percentile_lv = []
    for freq in oct_freq_masks.keys():
        percentile_lv.append(np.percentile(level[freq], percentile))

    return percentile_lv, level

def smirnov_grubbs(x: list, alpha: float):
    x_ini = x
    while(True):
        mean = np.mean(x)
        std = np.std(x, ddof=1)
        imax, imin = np.argmax(x), np.argmin(x)
        itest = imax if np.abs(x[imax] - mean) > np.abs(x[imin] - mean) else imin
        test =  np.abs(x[itest] - mean)/std
        n = len(x)
        t = stats.t.isf((alpha/n)/2, n-2)
        tau = (n-1)/np.sqrt(n) * np.sqrt(t**2/(n-2 + t**2))
        if(test > tau):
            x = np.delete(x, itest)
        else:
            break
    x_outlier = np.setdiff1d(x_ini,x)
    return x, x_outlier

def get_statics(data_list):

    n = len(data_list)
    std = round(np.std(data_list,ddof=1),3)
    se = round(std/np.sqrt(n),3)
    mean = round(np.mean(data_list),3)
    sk = round(skew(data_list),3)
    ku = round(kurtosis(data_list),3)

    return n,std,se,mean,sk,ku

# def cal_CPB_percentile_level(signal, center_freqs, oct_mask, tap, mean_time_sec, window, hop_len, fs, percentile):

#     frame_num = int(np.floor((signal.shape[0] - tap) / hop_len)) + 1
#     if frame_num < 1:
#         msg = f"失敗:データ長がFFT点数{tap}に満たない"
#         raise ValueError(msg)

#     if signal.shape[0] < mean_time * tap:
#         msg = f"失敗:データ長が指定の平均化時間{mean_time}秒に満たない"
#         raise ValueError(msg)
#     f=[]
#     data = []
#     L= np.array()
#     rfft = np.fft.rfft
#     hop_len_sec = hop_len * fs
#     mean_time_count = hop_len_sec
#     for i in range(frame_num):
#         frame = window * signal[(hop_len * i):(tap + (hop_len * i))]
#         f.append(rfft(frame, axis=0))
#         mean_time_count += hop_len_sec
#         if mean_time_count >= mean_time_sec:
#             S = (np.mean(np.abs(np.stack(f, axis=0)), axis=0))
#             for freq in center_freqs:
#                 data.append(10*np.log10(np.sum(S[oct_mask[str(freq)][:,0]], axis=0)))
#                 f = []
#                 data = []
#                 print(data)
    #         L= np.vstack(L,data)
    #         mean_time = hop_len_sec

    # return np.percentile(L, percentile, axis=1)

# def get_datum(signal, tap, oct_mask, fs, percentile):

#     mean_time = 0.1
#     window = sg.get_window("hamming",tap)
#     overlap_rate = 0.5
#     hop_len = int(tap * overlap_rate)

#     sub_data = signal[:,0]
#     slm_data = signal[:,1]
#     slm_peak_lv = cal_CPB_percentile_level(slm_data, oct_mask, tap, mean_time, window, hop_len, fs, percentile)
#     sub_peak_lv = cal_CPB_percentile_level(sub_data, oct_mask, tap, mean_time, window, hop_len, fs, percentile)
#     return slm_peak_lv - sub_peak_lv
