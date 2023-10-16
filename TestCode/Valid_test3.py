# -*- conding:UTF-8 -*-

"""
処理手順

1.periodA,periodBで指定した期間内の実音ファイルを読み込み、CPB分析、SLM-サブマイク差を算出
2.periodA,periodBの母平均の区間推定,信頼区間を求める
3.periodBの信頼区間がperiodAの信頼区間から大きく外れていたらtxtファイルにメッセージを出力
"""

import datetime
from pathlib import Path
import numpy as np
import wave
from scipy.io import wavfile
import os
import glob
# from typing import List, Tuple
import sys
import matplotlib.pyplot as plt
from scipy import stats

# submic_ch = 0 , slm_ch = 1

ID = "CH53"
DATA_DIR = Path(r"D:\Diana\新千歳空港\DATA")
WAVE_DIR = Path(r"D:\Diana\新千歳空港\WAVE")
SAVE_DIR = Path(r"D:\Diana\Program\SoundValid\workspace\testcode\感度低下検知検証\FIG")
LOG_DIR = Path(r"D:\Diana\Program\SoundValid\workspace\testcode\感度低下検知検証\LOG")
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

def cal_mean_interval(data,p):

    mean = np.mean(data)
    dvar = np.var(data,ddof=1)
    std = np.sqrt(dvar/len(data))
    dof = len(data) -1 

    bottom, up = stats.t.interval(p, dof, loc=mean, scale=std)

    return bottom, up

def do_valid(periodA, periodB, freq, p, mean_diff, exclusion = False, SN_check = False):
    
        
    fig_dir = os.path.join(SAVE_DIR,periodB[0].strftime('%Y%m%d'))
    if not os.path.exists(fig_dir): 
        os.makedirs(fig_dir)

    diffsA = get_params_period(ID,periodA[0], periodA[1], WAVE_DIR, freq, exclusion, SN_check)
    diffsB = get_params_period(ID,periodB[0], periodB[1], WAVE_DIR, freq, exclusion, SN_check)

    anormly_msg = ""
    if diffsA != -1 and diffsB != -1:
        
        intervalA = cal_mean_interval(diffsA,p)
        intervalB = cal_mean_interval(diffsB,p)

        if intervalA[0] - mean_diff > intervalB[1]:
            anormly_msg = periodB[0].strftime('%Y%m%d') + " " + str(freq) + " Hz"  + " 騒音計平均値低い or サブマイク高い"
        elif intervalA[1] + mean_diff < intervalB[0]:
            anormly_msg = periodB[0].strftime('%Y%m%d') + " " + str(freq) + " Hz" + " 騒音計平均値高い or サブマイク低い"
    
        fig = draw_hist(diffsA,diffsB,intervalA,intervalB,mean_diff)
        plt.title(periodB[0].strftime('%Y%m%d') + "_" + str(freq) + "Hz")
        fig.savefig(os.path.join(fig_dir,periodB[0].strftime('%Y%m%d') + "_" + str(freq) + "Hz.png"))
        plt.close()
    
    return anormly_msg

def make_oct_mask(ceter_freq, fft_f):

    oct_freq_l = ceter_freq / 2**(1 / 2)
    oct_freq_h = ceter_freq * 2**(1 / 2)
    oct_freq_mask = np.array([(fft_f >= oct_freq_l) & (fft_f < oct_freq_h)])

    return oct_freq_mask.reshape([-1,1])

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

def get_params_period(ID,st_time, ed_time, wave_dir, freq, exclusion = False, SN_check = False):

    days = get_date_range(st_time, ed_time)

    wav_list = []
    for day in days:

        target_dir = os.path.join(wave_dir,day.strftime('%Y%m'), ID, day.strftime('%Y%m%d'))
        
        if os.path.isdir(target_dir) == True:
            wav_list += glob.glob(os.path.join(target_dir,'**','*.WAV'),recursive = True)
        else:
            # print("失敗:対象日のWAVEディレクトリが存在しません:", target_dir)
            return -1

    if wav_list == []:
        # print("失敗:対象期間内にWAVEファイルが存在しません:[",st_time,"~",ed_time,"]")
        return -1
    
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

            if SN_check == True:
                # SNRのチェック
                if slm_lv > SLM_NOISE_LEVEL[str(freq)] + SNR:
                    diffs.append(slm_lv - sub_lv)
                else:
                    print("SNRが自己雑音 + 10dBに満たない[",file,"]")
            else:
                diffs.append(slm_lv - sub_lv)
            
    if exclusion == True:
        check = smirnov_grubbs(np.array(diffs), 0.05)
        # print("除外データ:",check[1],"\n外れ値数[",check[1].size,"]")
        diffs = list(check[0])

    # print("データ抽出期間[",st_time,"~",ed_time,"]")
    # print("サンプルサイズ[",len(diffs),"]")
    # print("---")
    
    if len(diffs) <= 0:
        print("検定可能サンプルなし")
        return -1
    
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

def draw_hist(a,b,a_int,b_int,mean_diff):

    fig = plt.figure()
    plt.hist(a,alpha = 0.5, label='periodA',bins = 10)
    plt.hist(b,alpha = 0.5, label='periodB',bins = 10)

    plt.axvline(np.mean(a), color='blue', linestyle='dashed', linewidth=1)
    plt.axvspan(a_int[0], a_int[1], color="skyblue",alpha = 0.3)

    plt.axvline(np.mean(b), color='orangered', linestyle='dashed', linewidth=1)
    plt.axvspan(b_int[0], b_int[1], color="coral",alpha = 0.5)

    if mean_diff != 0:
        plt.axvspan(a_int[0] - mean_diff, a_int[0], color="lightgreen",alpha = 0.3)
        plt.axvspan(a_int[1], a_int[1] + mean_diff, color="lightgreen",alpha = 0.3)

    plt.legend(loc='upper left') 
    
    return fig

def main():

    ######################################################################################
    # 対象オクターブバンド分析周波数
    # freq = 1000
    # 読み込んだデータからsmirnov_grubbs検定で外れ値を除くかどうか
    exclusion = True
    # オクターブバンド分析結果のSNRチェック
    SN_check = False
    # データを抽出する期間A 校正直後のデータを想定
    periodA = [datetime.datetime(2022,12,1,0,0,0),datetime.datetime(2022,12,1,23,59,59)]
    # データを抽出する期間B 異常検知したい期間のデータを想定
    # periodB = [datetime.datetime(2023,7,3,0,0,0),datetime.datetime(2023,7,3,23,59,59)]
    # 信頼区間推定の水準
    p = 0.95
    # 許される平均値のずれ
    mean_diff = 0.5
    ######################################################################################

    ret_day = 1
    msg_list = []
    count = 1
    while 1:
        day = datetime.datetime.today() - datetime.timedelta(days = count)
        periodB = [day.replace(hour=0,minute=0,second=0,microsecond=0),day.replace(hour=23,minute=59,second=59,microsecond=0)]

        for freq in FREQS:
            msg = do_valid(periodA, periodB, freq, p, mean_diff, exclusion, SN_check)
            if msg != "":
                msg_list.append(msg)

        count += 1
        diff = periodB[0] - periodA[0]

        if diff.days < 2 or count > ret_day:
            break

    if msg_list != []:
        msg_list.insert(0, "SN_check = " + str(SN_check))
        msg_list.insert(0, "exclusion = " + str(exclusion))
        fname = datetime.datetime.today() - datetime.timedelta(days = 1)
        with open(os.path.join(LOG_DIR,fname.strftime("%Y%m%d")) + ".txt", 'x') as f:
            for msg in msg_list:
                f.write(msg + "\n")
    
if __name__ == '__main__':
    main()