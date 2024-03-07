from datetime import datetime, timedelta
import os
import glob
import numpy as np
import wave
from scipy.io import wavfile
from scipy import signal as sg
from scipy import stats
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

def get_target_event_time(stid, wav_directory, st_time, next=False, direction="advance"):

    if next == True and direction == "advance":
        st_time = (st_time + timedelta(days = 1)).replace(hour = 0, minute = 0, second = 0)
    elif next == True and direction == "backward":
        st_time = (st_time - timedelta(days = 1)).replace(hour = 23, minute = 59, second = 59)

    if st_time.date() >= datetime.now().date() and next == False:
        msg = "st_timeは今日より前の日付を指定して下さい:{}".format(st_time)
        return False, msg

    elif st_time.date() >= datetime.now().date() and next == True and direction == "advance":
        msg = "{}-今日より先の日付は探せない-{}".format(stid,st_time.date())
        return False, msg

    elif st_time.date() < datetime(year=2022,month=12,day=1).date() and next == True and direction == "backward":
        msg = "{}-これ以上前の日付は探せない:{}".format(stid, datetime(year=2022,month=12,day=1))
        return False, msg

    target_dir = os.path.join(wav_directory, st_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'))

    if os.path.isdir(target_dir) == False:
        return get_target_event_time(stid, wav_directory, st_time, next = True, direction = direction)

    wav_list = glob.glob(os.path.join(target_dir,'**','*.WAV'), recursive = True)

    if wav_list == []:
        return get_target_event_time(stid, wav_directory, st_time, next = True, direction = direction)

    day_event_time_list = []
    for file in wav_list:
        fname = os.path.splitext(os.path.basename(file))[0]
        day_event_time_list.append(datetime.strptime(fname, '%y%m%d%H%M%S'))
    wav_list.clear()

    if direction == "advance":
        day_event_time_list = sorted(day_event_time_list,reverse=False)
    elif direction == "backward":
        day_event_time_list = sorted(day_event_time_list,reverse=True)

    # waveファイル名から騒音イベント時刻を得て指定時間との差を求める
    for event_time in day_event_time_list:

        if direction == "advance":
            if event_time == st_time or event_time >= st_time:
                path = os.path.join(wav_directory, event_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'),
                                    datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
                # 成功
                return event_time, path
        elif direction == "backward":
            if event_time == st_time or event_time <= st_time:
                path = os.path.join(wav_directory, event_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'),
                                    datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
                # 成功
                return event_time, path

    return get_target_event_time(stid, wav_directory, st_time, next = True, direction = direction)

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