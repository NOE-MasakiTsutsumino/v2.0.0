# -*- conding:UTF-8 -*-

"""
処理手順
1.caliblation_timeで指定した時刻から指定数の実音ファイルを読込、CPB分析、SLM-サブマイク差を算出
※caliblation_timeとは、点検にて騒音計Micの校正が完了した時刻を想定
2.算出したパラメータに外れ値が含まれているかチェックし、外れ値があれば除外する
3.2で外れ値を除外した場合、除外した数分の実音ファイルを読込パラメータ算出、以後パラメータが指定数になるまで繰り返す
4.算出したパラメータの母平均の区間推定,信頼区間を求める

5.periodで指定した検査期間内の実音ファイルを読み込み、CPB分析、SLM - サブマイク差を算出
6.検査期間内の母平均の区間推定,信頼区間を求める
7.6で求めた平均信頼区間が4で求めた平均信頼区間から大きく外れていたらtxtファイルにメッセージを出力


所感
騒音計マイクもしくはサブマイクが壊れていないか、どうか程度は検出できる
平均値が大きくずれている場合、サブマイクもしくは騒音計どちらかの信号が異常であろうことしかわからないので
サブマイクもしくは騒音計の信号どちらが異常かを突き止める機能を追加する必要がある
月に数日、サブマイクの実音が風切り音か何かで荒ぶって差が生じていることがある。これらをいちいち検知していると煩いので↑の機能が必要

感度異常の検知に適した校正直後のデータに関するサンプルサイズを知るために、データの標準偏差などを保存してどの程度で
収まっているのか知る必要がある

日によってサブマイクのレベルが上がったり下がったりしているっぽい？

95%信頼区間の求め方がtest4まで間違っていた。
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
# WAVE_DIR = Path(r"D:\Diana\Program\SoundValid\workspace\testcode\感度低下検知検証\TEST_WAVE")
WAVE_DIR = Path(r"D:\Diana\新千歳空港\WAVE")
SAVE_DIR = Path(r"D:\Diana\Program\SoundValid\workspace\testcode\感度低下検知検証\TEST_FIG")
LOG_DIR = Path(r"D:\Diana\Program\SoundValid\workspace\testcode\感度低下検知検証\TEST_LOG")
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

    """
    分布の母平均信頼区間を求める
    """

    # 形状パラメータ(自由度)を指定
    dof = len(data) -1
    # 位置パラメータを指定
    mean = np.mean(data)
    # 尺度パラメータを指定
    scale = np.std(data)

    t_data = stats.t(loc=mean,scale=scale,df=dof)
    bottom, up = t_data.interval(alpha=p)

    return bottom, up

def do_valid(diffsA, diffsB, p, tolerance):
    """
    異常検知の実行
    """

    intervalA = cal_mean_interval(diffsA,p)
    intervalB = cal_mean_interval(diffsB,p)

    if intervalA[0] - tolerance > intervalB[1]:
        jdg = 1
        return jdg ,intervalA ,intervalB
    elif intervalA[1] + tolerance < intervalB[0]:
        jdg = 2
        return jdg ,intervalA ,intervalB

    return 0 ,intervalA ,intervalB

def make_oct_mask(ceter_freq, fft_f):
    """
    オクターブバンドフィルタ作成
    """

    oct_freq_l = ceter_freq / 2**(1 / 2)
    oct_freq_h = ceter_freq * 2**(1 / 2)
    oct_freq_mask = np.array([(fft_f >= oct_freq_l) & (fft_f < oct_freq_h)])

    return oct_freq_mask.reshape([-1,1])

def wav_load(wav_path) -> np.ndarray:
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

    """
    信号と周波数をもらって、オクターブバンドレベルを求める
    """
    _freqs = [125,250,500,1000,2000,4000]
    
    fs  = 12000
    n_fft = 4096
    hop_sep = 2
    hop_len = n_fft // hop_sep
    fft_f: np.ndarray = np.fft.rfftfreq(n_fft,1/fs)
    # fft_f: np.ndarray = np.fft.rfftfreq(n_fft) * fs
    win = np.blackman(n_fft)

    if center_freq not in _freqs:
        print(f'分析対象外の周波数。freqは {_freqs}の何れかを選択してください. ')
        return -1
    
    fil = make_oct_mask(center_freq,fft_f)
    frame_num = int(np.floor((data.shape[0] - n_fft) / hop_len)) + 1

    if frame_num < 1:
        print(f"Error:信号長がFFT点数 %d に満たないのでダメです" % n_fft)
        return -1
    
    rfft = np.fft.rfft

    f = []
    for i in range(frame_num):
        frame = win * data[(hop_len * i):(n_fft + (hop_len * i))]
        f.append(rfft(frame, axis=0))

    S = (np.mean(np.abs(np.stack(f, axis=0)), axis = 0))
    result = 10 * np.log10(np.sum(S[fil[:,0]], axis = 0))
    return result

def _func_tau(x, alpha):
    """
    smirnov_grubbs用の変数算出
    """
    n = x.size
    t = stats.t.isf((alpha/n)/2, n-2) #両側
    tau = (n-1)/np.sqrt(n) * np.sqrt(t**2/(n-2 + t**2))
    return tau

def smirnov_grubbs(x, alpha):
    """
    外れ値の検定と削除
    """
    x_ini = x
    while(True):
        mean = np.mean(x)
        std = np.std(x, ddof=1)
        imax, imin = np.argmax(x), np.argmin(x)
        itest = imax if np.abs(x[imax] - mean) > np.abs(x[imin] - mean) else imin

        test =  np.abs(x[itest] -mean)/std
        tau = _func_tau(x, alpha)

        if(test > tau):
            x = np.delete(x, itest)
        else:
            break

    x_outlier = np.setdiff1d(x_ini,x) 
    return x, x_outlier

def get_params_period(ID,st_time, ed_time, wave_dir, freq, exclusion = False, SN_check = False):
    """
    st_time, ed_timeで指定した期間内の実音ファイルからパラメータ算出
    """
    days = _get_date_range(st_time, ed_time)

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

            # tex = ", band: {:.4g} Hz , slm: {:.3g} dB , sub: {:.3g} dB"
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

def _get_date_range(st_time, ed_time):

    if (ed_time - st_time).days < 0:
        print("エラー: ed_time は st_time より後の時刻を指定して下さい")
        sys.exit()

    sd = st_time.date()
    day_list = [sd]

    for i in range((ed_time - st_time).days):
        day_list.append(sd + datetime.timedelta(days = i + 1))

    return day_list

def get_params_calibrated(ID, st_time, freq, num, wav_dir, diffs = None, exclusion = False, SN_check = False):

    time = st_time

    if diffs == None:
        diffs = []

    # パラメータが指定数になるまでループ処理
    while len(diffs) < num:

        event_time, path = _get_target_event_time(ID, time, wav_dir)

        data = wav_load(path)
        sub_data = data[:,0]
        slm_data = data[:,1]

        slm_lv = cal_CPB_level(slm_data,freq)
        sub_lv = cal_CPB_level(sub_data,freq)
        # tex = ", band: {:.4g} Hz , slm: {:.3g} dB , sub: {:.3g} dB ,"

        if SN_check == False or slm_lv > SLM_NOISE_LEVEL[str(freq)] + SNR:
            diffs.append(slm_lv - sub_lv)
        
        time = event_time + datetime.timedelta(seconds = 1)

    if exclusion == True:
        check = smirnov_grubbs(np.array(diffs), 0.05)
        # print("除外データ:",check[1],"外れ値個数:",check[1].size)
        diffs = list(check[0])

    if len(diffs) == num:
        # print("データ抽出期間[",st_time,"~",event_time,"]")
        # print("データ数:", num)
        return diffs
    
    return get_params_calibrated(ID, time, freq, num, wav_dir, diffs, exclusion = exclusion, SN_check = SN_check)

def _get_target_event_time(ID, st_time, wav_dir, advance = False):

    """
    st_timeから過去へ遡り、最も近い騒音イベント時刻を取得する
    探索対象は実音ファイルファイル名
    """
    if st_time.date() >= datetime.datetime.now().date() and advance == False:
        print("失敗:st_timeは現在日より前の日付を指定して下さい")
        sys.exit()
    elif st_time.date() >= datetime.datetime.now().date() and advance == True:
        print("失敗:必要データ数が集まりませんでした")
        sys.exit()

    if advance == True:
        st_time = st_time + datetime.timedelta(days=1)
        st_time = st_time.replace(hour=0, minute=0, second=0)

    target_dir = os.path.join(wav_dir,st_time.strftime('%Y%m'),ID,st_time.strftime('%Y%m%d'))
    
    if os.path.isdir(target_dir) == False:
        print("失敗:対象日のディレクトリが存在しません:",target_dir)
        return _get_target_event_time(ID, st_time, wav_dir, advance = True)
    
    wav_list = glob.glob(os.path.join(target_dir,'**','*.WAV'), recursive=True)

    if wav_list == []:
        print("失敗:対象ディレクトリ内にWAVEファイルが存在しません:",target_dir)
        return _get_target_event_time(ID, st_time, wav_dir, advance = True)
    
    day_event_time_list = []
    for file in wav_list:
        fname = os.path.splitext(os.path.basename(file))[0]
        day_event_time_list.append(datetime.datetime.strptime(fname, '%y%m%d%H%M%S'))
    wav_list.clear()

    day_event_time_list = sorted(day_event_time_list,reverse=False)

    # 対象Dファイルから騒音イベント時刻を抜き出して指定時間との差を求める
    for event_time in day_event_time_list:
   
        time_lag = event_time - st_time
        # print(st_time,"-",event_time,"=",time_lag)

        if time_lag == datetime.timedelta() or time_lag.days >= 0:
            path = os.path.join(wav_dir,event_time.strftime('%Y%m'),ID,st_time.strftime('%Y%m%d'),
                                datetime.datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
            return event_time, path

    return _get_target_event_time(ID, st_time, wav_dir, advance = True)

def draw_hist(a,b,a_int,b_int,mean_diff):
    """
    結果分析用のヒストグラム画像オブジェクトを作るよ
    """

    dof_a = len(a) -1
    mean_a = np.mean(a)
    scale_a = np.std(a)

    dof_b = len(b) -1
    mean_b = np.mean(b)
    scale_b = np.std(b)

    x_a = np.linspace(start= mean_a-scale_a*5, stop = mean_a + scale_a*5, num=251)
    density_a = stats.t.pdf(x=x_a, df=dof_a, loc=mean_a, scale=scale_a)

    x_b = np.linspace(start= mean_b-scale_b*5, stop = mean_b + scale_b*5, num=251)
    density_b = stats.t.pdf(x=x_b, df=dof_b, loc=mean_b, scale=scale_b)

    fig = plt.figure()
    plt.hist(a,alpha = 0.5, label='Calibrated',bins = 10)
    plt.hist(b,alpha = 0.5, label='Target',bins = 10)

    plt.plot(x_a, density_a, color='blue') # 折れ線グラフ
    plt.plot(x_b, density_b, color='orangered') # 折れ線グラフ

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
    # 読み込んだデータからsmirnov_grubbs検定で外れ値を除くかどうか
    exclusion = False
    # オクターブバンド分析結果のSNRチェック
    SN_check = False
    # データを抽出する期間A 校正した直後の時間を想定
    caliblation_time = datetime.datetime(2022,12,1,0,0,0)
    # 信頼区間推定の水準
    p = 0.95
    # 許される平均値のずれ
    tolerance = 0.3
    # 遡って異常検知を実行する日数
    ret_day = 1
    # 
    num = 30
    ######################################################################################

    msg_list = []

    process_start_time = datetime.datetime.now()
    
    diffsA = dict()
    for freq in FREQS:
        diffsA[str(freq)] = get_params_calibrated(ID, caliblation_time, freq, num, WAVE_DIR, exclusion = exclusion, SN_check = SN_check)

    count = 1
    while 1:
        day = datetime.datetime.today() - datetime.timedelta(days = count)
        period = [day.replace(hour=0,minute=0,second=0,microsecond=0),day.replace(hour=23,minute=59,second=59,microsecond=0)]
        
        fig_dir = os.path.join(SAVE_DIR,period[0].strftime('%Y%m%d'))
        if not os.path.exists(fig_dir): 
            os.makedirs(fig_dir)

        for freq in FREQS:
            diffsB = get_params_period(ID,period[0], period[1], WAVE_DIR, freq, exclusion, SN_check)

            jdg ,intervalA ,intervalB = do_valid(diffsA[str(freq)], diffsB, p, tolerance)
            if  jdg == 1:
                msg = period[0].strftime('%Y%m%d') + " " + str(freq) + " Hz"  + " 騒音計平均値低い or サブマイク高い"
                msg_list.append(msg)
            elif jdg == 2:
                msg = period[0].strftime('%Y%m%d') + " " + str(freq) + " Hz" + " 騒音計平均値高い or サブマイク低い"
                msg_list.append(msg)
    
            fig = draw_hist(diffsA[str(freq)], diffsB, intervalA, intervalB, tolerance)
            plt.title(period[0].strftime('%Y%m%d') + "_" + str(freq) + "Hz")
            fig.savefig(os.path.join(fig_dir,period[0].strftime('%Y%m%d') + "_" + str(freq) + "Hz.png"))
            plt.close()

        count += 1
        diff = period[0] - caliblation_time

        if diff.days < 2 or count > ret_day:
            break
        
    msg_list.insert(0,"---以下検知した異常一覧---")
    msg_list.insert(0, "騒音計信号SNRチェック処理 = " + str(SN_check))
    msg_list.insert(0, "外れ値除外処理 = " + str(exclusion))
    msg_list.insert(0, "騒音計マイク校正後データ サンプルサイズ =  " + str(num))
    msg_list.insert(0, "騒音計マイク校正完了時刻 " + str(caliblation_time))
    msg_list.insert(0, "実行時刻 " + str(process_start_time))
    
    fname = datetime.datetime.today() - datetime.timedelta(days = 1)
    with open(os.path.join(LOG_DIR,"valid_" + fname.strftime("%Y%m%d")) + ".txt", 'a') as f:
        for msg in msg_list:
            f.write(msg + "\n")

if __name__ == '__main__':
    main()