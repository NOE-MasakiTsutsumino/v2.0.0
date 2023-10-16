# -*- conding:UTF-8 -*-

"""
処理手順

1.処理対象の測定局実音データを対象日付から過去へ遡りながら新しい順に1件ずつ読み込み、処理に使えるか判定
2.処理に使えるデータ数が指定件数以上になったら読み込みをやめる
3.読み込んだデータにより異常検知を行う

"""

import datetime
from pathlib import Path
import numpy as np
import wave
from scipy.io import wavfile
import os
import glob
from typing import List, Tuple
import sys
import matplotlib.pyplot as plt
from scipy import stats

ID = "CH53"
DATA_DIR = Path(r"D:\Diana\新千歳空港\DATA")
WAVE_DIR = Path(r"D:\Diana\新千歳空港\WAVE")
SAVE_DIR = Path(r"D:\Diana\Program\SoundValid\workspace\testcode\感度低下検知テストプログラム\SAVE")
START_TIME = datetime.datetime(2023,6,27,23,59,59)
AVE_NUM = 50
SNR = 10
FREQS = [125,250,500,1000,2000,4000]
SLM_NOISE_LEVEL = {
    "125":  30,
    "250":  30,
    "500":  30,
    "1000": 30,
    "2000": 30,
    "4000": 30
}

def main():

    freq = 125
    exclusion = False
    periodA = [datetime.datetime(2022,12,1,0,0,0),datetime.datetime(2022,12,1,23,59,59)]
    periodB = [datetime.datetime(2022,12,3,0,0,0),datetime.datetime(2022,12,3,23,59,59)]

    diffsA = get_params_period(ID,periodA[0], periodA[1], WAVE_DIR, freq, exclusion)
    diffsB = get_params_period(ID,periodB[0], periodB[1], WAVE_DIR, freq, exclusion)

    p = 0.05 #　有意水準
    func = 2 # 1:下片側検定 2:上片側検定 3:両側検定

    t_value, p_value, result = welch_ttest(diffsA, diffsB, p, func)

    # alternative="less"        a < bかどうか
    # alternative="greater"     a > bかどうか
    # t_value, p_value = stats.ttest_ind(diffsA, diffsB, equal_var=False)

    # print("t_value:", t_value)                                                                                                                                                                      
    # print("p_value:", p_value)
    
    # if p_value < 0.05:
    #     print(f"p = {p_value:.3f} のため、帰無仮説が棄却されました。AとBに差があります")
    # else:
    #     print(f"p = {p_value:.3f} のため、帰無仮説が採択されました。AとBに差はありません")

    bins = np.linspace(-10, 10, 50)
    plt.hist(diffsA,alpha = 0.5, label='periodA')
    plt.hist(diffsB,alpha = 0.5, label='periodB')
    plt.legend(loc='upper left')
    plt.show()

    # if AVE_NUM < 2:
    #     print("データ数は2以上必要 指定数:",AVE_NUM)
    #     sys.exit()

    # time  = START_TIME
    # for i in range(30):
    #     diffs = get_statics(ID, time, 500, exclusion = True)
    #     print("平均:",np.mean(diffs),"標準偏差:",np.std(diffs),"データ数:",AVE_NUM)

    #     # stats.probplot(diffs, plot=plt)
    #     plt.hist(diffs,bins = 16)
    #     plt.show()

    #     res  = ", 正規分布です"
    #     p0 = stats.shapiro(diffs)[1]
    #     if p0 <= 0.05:
    #         res = ", 正規分布ではない"
    #     print("p値:",round(p0,3),res)

    #     time = time - datetime.timedelta(days = 1)

def make_oct_mask(ceter_freq, fft_f):

    oct_freq_l = ceter_freq / 2**(1 / 2)
    oct_freq_h = ceter_freq * 2**(1 / 2)
    oct_freq_mask = np.array([(fft_f >= oct_freq_l) & (fft_f < oct_freq_h)])

    return oct_freq_mask.reshape([-1,1])

def get_target_event_time(ID, st_time, dir):

    """
    st_timeから過去へ遡り、最も近い騒音イベント時刻を取得する
    探索対象は実音ファイルのファイル名
    """
    
    # st_timeから対象日の実音ファイルディレクトリパスを取得
    target_dir = os.path.join(dir,st_time.strftime('%Y%m'),ID,st_time.strftime('%Y%m%d'))
    
    if os.path.isdir(target_dir) == False:
        print("失敗:ディレクトリが存在しません:",target_dir)
        sys.exit()
    
    # 対象日の実音ファイルリストを取得
    wav_list = glob.glob(os.path.join(target_dir,'**','*.WAV'),recursive=True)

    if wav_list == []:
        print("失敗:対象ディレクトリ内にWAVEファイルが存在しません:",target_dir)
        sys.exit()
    
    day_event_time_list = []
    for file in wav_list:
        fname = os.path.splitext(os.path.basename(file))[0]
        day_event_time_list.append(datetime.datetime.strptime(fname, '%y%m%d%H%M%S'))
    wav_list.clear()

    day_event_time_list = sorted(day_event_time_list,reverse=True)

    # 対象Dファイルから騒音イベント時刻を抜き出して指定時間との差を求める
    for event_time in day_event_time_list:
   
        time_lag = st_time - event_time
        # print(st_time,"-",event_time,"=",time_lag)

        if time_lag == datetime.timedelta() or time_lag.days >= 0:
            path = os.path.join(dir,event_time.strftime('%Y%m'),ID,st_time.strftime('%Y%m%d'),
                                datetime.datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
            return event_time, path

    ret_time = st_time - datetime.timedelta(days = 1)
    ret_time = ret_time.replace(hour=23, minute=59, second=59)

    return get_target_event_time(ID, ret_time, dir)
  
    # Dファイルの騒音イベント時刻を参照しようとしたパターン      
    # Dfilename = st_time.strftime('%y') + "_" + st_time.strftime('%m') + "_" + st_time.strftime('%d') + ".D" + re.sub( r'\D', '', ID)
    # path = os.path.join(dir,st_time.strftime('%Y%m'),ID,Dfilename)

def wav_load(wav_path: Path) -> np.ndarray:
    """実音データwavefile読み込み

    Args:
        wav_path (Path): wavefileのfullpath
        slm_ch (int): 騒音計信号のindex 基本SubMicが0,SLMが1

    Raises:
        ValueError: openしたwaveのch数が2でなければならない
        ValueError: openしたwaveのsamplerateは12000でなければならない
    Returns:
        numpy array: stereo signalのsample値
    """

    if os.path.exists(wav_path) == False:
        raise ValueError(f"wave file not found: {wav_path}")

    with wave.open(wav_path, 'rb') as wv:
        n_ch = wv.getnchannels()
        # fs = wv.getframerate()
    if n_ch != 2:
        raise ValueError(f"ステレオ信号ではありません: {wav_path}")
    # elif fs != fs:
    #     raise ValueError(f"サンプリング周波数が対象外です: {wav_path}")
    # 対象ファイルの読み込み
    _, data = wavfile.read(wav_path)
    # if slm_ch == 1:
    #     # 騒音計音声がindex:0となるようにch.入れ替え
    #     data = data[:, ::-1]
    return data

def cal_CPB_level(data,center_freq):
    _freqs = [125,250,500,1000,2000,4000]
    
    fs  = 12000
    n_fft = 4096
    hop_sep = 2
    hop_len = n_fft // hop_sep
    fft_f: np.ndarray = np.fft.rfftfreq(n_fft) * fs
    win = np.blackman(n_fft)

    if center_freq not in _freqs:
        raise ValueError(f'分析対象外の周波数。freqは {_freqs}の何れかを選択してください. ')
    
    fil = make_oct_mask(center_freq,fft_f)
    frame_num = int(np.floor((data.shape[0] - n_fft) / hop_len)) + 1

    if frame_num < 1:
        raise ValueError(f"Error:信号長がFFT点数 %d に満たないのでダメです" % n_fft)
    
    rfft = np.fft.rfft

    f = []
    for i in range(frame_num):
        frame = win * data[(hop_len * i):(n_fft + (hop_len * i))]
        f.append(rfft(frame, axis=0))

    S = (np.mean(np.abs(np.stack(f, axis=0)), axis = 0))
    result = 10 * np.log10(np.sum(S[fil[:,0]], axis = 0))
    return result

def func_tau(x, alpha):
    n = x.size
    t = stats.t.isf((alpha/n)/2, n-2) #両側
    tau = (n-1)/np.sqrt(n) * np.sqrt(t**2/(n-2 + t**2))
    return tau

def smirnov_grubbs(x, alpha):
    x_ini = x
    while(True):
        mean = np.mean(x)
        std = np.std(x, ddof=1)
        imax, imin = np.argmax(x), np.argmin(x)
        itest = imax if np.abs(x[imax] - mean) > np.abs(x[imin] - mean) else imin

        test =  np.abs(x[itest] -mean)/std
        tau = func_tau(x, alpha)

        if(test > tau):
            x = np.delete(x, itest)
        else:
            break

    x_outlier = np.setdiff1d(x_ini,x) 
    return x, x_outlier

def get_params_period(ID,st_time, ed_time, wave_dir, freq, exclusion = False):

    days = get_date_range(st_time, ed_time)

    wav_list = []
    for day in days:

        target_dir = os.path.join(wave_dir,day.strftime('%Y%m'), ID, day.strftime('%Y%m%d'))
        
        if os.path.isdir(target_dir) == True:
            wav_list += glob.glob(os.path.join(target_dir,'**','*.WAV'),recursive = True)
        else:
            print("注意:対象日のWAVEディレクトリが存在しません:", target_dir)

    if wav_list == []:
        print("失敗:対象期間内にWAVEファイルが存在しません:[",st_time,"~",ed_time,"]")
        print("処理を終了します")
        sys.exit()
    
    diffs = []
    for file in wav_list:
        eve_time = datetime.datetime.strptime(os.path.splitext(os.path.basename(file))[0], '%y%m%d%H%M%S')

        if eve_time >= st_time and eve_time <= ed_time:
            data = wav_load(file)
            sub_data = data[:,0]
            slm_data = data[:,1]
            slm_lv = cal_CPB_level(slm_data,freq)
            sub_lv = cal_CPB_level(sub_data,freq)
            tex = ", band: {:.4g} Hz , slm: {:.3g} dB , sub: {:.3g} dB"
            # print(eve_time,tex.format(freq,slm_lv, sub_lv))
            diffs.append(slm_lv - sub_lv)
    
    if exclusion == True:
        check = smirnov_grubbs(np.array(diffs), 0.05)
        print("除外データ:",check[1],"\n外れ値数[",check[1].size,"]")
        diffs = list(check[0])

    print("データ抽出期間[",st_time,"~",ed_time,"]")
    print("サンプルサイズ[",len(diffs),"]")
    
    if len(diffs) <= 0:
        print("サンプルなし 処理を終了します")
        sys.exit()
    return diffs

def get_date_range(st_time, ed_time):

    if (ed_time - st_time).days < 0:
        print("エラー: ed_time は st_time より後の時刻を指定して下さい")
        sys.exit()

    sd = st_time.date()
    day_list = [sd]

    for i in range((ed_time - st_time).days):
        day_list.append(sd + datetime.timedelta(days = i + 1))

    return day_list

def get_statics(ID, st_time, oct_center, diffs = None, exclusion = False):

    time = st_time

    if diffs == None:
        diffs = []

    # パラメータが指定数になるまでループ処理
    while len(diffs) < AVE_NUM:

        eve_time, path = get_target_event_time(ID, time, WAVE_DIR)
        data = wav_load(path)
        sub_data = data[:,0]
        slm_data = data[:,1]

        slm_lv = cal_CPB_level(slm_data,oct_center)
        sub_lv = cal_CPB_level(sub_data,oct_center)
        tex = ", band: {:.4g} Hz , slm: {:.3g} dB , sub: {:.3g} dB ,"

        # SNRのチェック
        if slm_lv > SLM_NOISE_LEVEL[str(oct_center)] + SNR:
            flag = True
            diffs.append(slm_lv - sub_lv)
        else:
            flag = False

        # print(eve_time, tex.format(oct_center,slm_lv, sub_lv),"SNR:",flag,", num:",len(diffs))

        # for f in freqs:
        #     x = cal_CPB_level(slm,f)
        #     y = cal_CPB_level(sub,f)
        #     diffs.append(x - y)
        # diff_array = np.vstack((diff_array,np.array(diffs)))

        time = eve_time - datetime.timedelta(seconds = 1)

    if exclusion == True:
        check = smirnov_grubbs(np.array(diffs), 0.05)
        # print("除外データ:",check[1],"外れ値個数:",check[1].size)
        diffs = list(check[0])

    if len(diffs) == AVE_NUM:
        print("データ抽出期間[",st_time,"~",eve_time,"]")
        # print("データ数:", AVE_NUM)
        return diffs
    
    return get_statics(ID, time, oct_center, diffs, exclusion = exclusion)

def welch_ttest(a :list, b: list, p: float ,func = 3):

    n_a = len(a)
    n_b = len(b)
    mean_a = np.mean(a)
    mean_b = np.mean(b)
    dvar_a = np.var(a,ddof=1)
    dvar_b = np.var(b,ddof=1)
    std_a = np.sqrt(dvar_a)
    std_b = np.sqrt(dvar_b)

    buf = (std_a**2 / n_a) + (std_b**2 / n_b)
    t_value = (mean_a - mean_b) / np.sqrt(buf)
    dof = buf**2 / ( ( dvar_a**2/ (n_a**2 * (n_a - 1)) ) + (dvar_b**2/ (n_b**2 * (n_b - 1) ) ) )

    p_value = stats.t.sf(abs(t_value), dof)

    print("---")

    if func == 1 :
        # aはbより小さい
        print("Welchのt検定[下片側検定]を実行します")
        t = abs(stats.t.ppf(p, dof))

    elif func == 2:
        # aはbより大きい
        print("Welchのt検定[上片側検定]を実行します")
        t =  abs(stats.t.ppf(p, dof))
        p_value = 1- p_value
    
    elif func == 3:
        # aはbと異なる
        print("Welchのt検定[両側検定]を実行します")
        t =  abs(stats.t.ppf(p/2, dof))
        p_value = p_value * 2
    
    else:
        print("funcは 1 :下片側検定もしくは 2 :上片側検定 もしくは 3: 両側検定 を指定して下さい")
        sys.exit()

    if p_value < p:
        print(f"p値[{p_value:.3f}] < 優位水準[{p:.3f}] のため、帰無仮説が棄却されました。AとBに差があります")
        result = True
    else:
        print(f"p値[{p_value:.3f}] > 優位水準[{p:.3f}] のため、帰無仮説が採択されました。AとBに差はありません")
        result = False

    print("t_value:", t_value)                                                                                                                                                                      
    print("p_value:", p_value)
    print("---")

    return t_value, p_value, result

if __name__ == '__main__':
    main()