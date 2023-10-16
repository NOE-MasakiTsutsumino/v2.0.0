# -*- conding:UTF-8 -*-

"""
Valid_test8.py
2023/07/11 masaki tsutsumino 作成

処理手順
1.caliblation_timeで指定した時刻から後の時間を探して指定数の実音ファイルを読込、CPB分析、SLM-サブマイク差を算出
※caliblation_timeとは、点検にて騒音計Micの校正が完了した時刻を想定
2.算出したパラメータに外れ値が含まれているかチェックし、外れ値があれば除外する(処理を行うかどうかTrue,Falseで選択できる)
3.2で外れ値を除外した場合、除外した数分の実音ファイルを読込パラメータ算出、以後パラメータが指定数になるまで繰り返す
4.算出したパラメータの母平均の区間推定,信頼区間を求める

5.実行時刻から遡って指定した数の実音ファイルを読み込み、CPB分析、SLM - サブマイク差を算出
7.6で求めた値が平均信頼区間から大きく外れていたらtxtファイルにメッセージを出力
実音データ一つ一つを確認する方法

所感
騒音計マイクもしくはサブマイクが壊れていないか、どうか程度は検出できる
平均値が大きくずれている場合、サブマイクもしくは騒音計どちらかの信号が異常であろうことしかわからないので
サブマイクもしくは騒音計の信号どちらが異常かを突き止める機能を追加する必要がある
月に数日、サブマイクの実音が風切り音か何かで荒ぶって差が生じていることがある。これらをいちいち検知していると煩いので↑の機能が必要

感度異常の検知に適した校正直後のデータに関するサンプルサイズを知るために、データの標準偏差などを保存してどの程度で
収まっているのか知る必要がある

日によってサブマイクのレベルが上がったり下がったりしているっぽい？

95%信頼区間の求め方がtest4まで間違っていた。test5から修正
分散が大きい日は評価しない
感度低下 - 平均値の比較は標本分散がある程度に落ち着くまでデータを選んでから評価する
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
FREQS = [500,1000,2000]
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

def do_valid(intervalA, data, tolerance):
    """
    異常検知の実行
    """

    if intervalA[0] - tolerance > data:
        jdg = 1
        return jdg
    elif intervalA[1] + tolerance < data:
        jdg = 2
        return jdg

    return 0

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
            print("失敗:対象日のWAVEディレクトリが存在しません:", target_dir)
            return -1,-1

    if wav_list == []:
        print("失敗:対象期間内にWAVEファイルが存在しません:[",st_time,"~",ed_time,"]")
        return -1,-1
    
    diffs = []
    fname_list = []
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
                    fname_list.append(os.path.basename(file))
                else:
                    print("SNRが自己雑音 + 10dBに満たない[",file,"]")
            else:
                diffs.append(slm_lv - sub_lv)
                fname_list.append(os.path.basename(file))
            
    if exclusion == True:
        check = smirnov_grubbs(np.array(diffs), 0.05)
        # print("除外データ:",check[1],"\n外れ値数[",check[1].size,"]")
        diffs = list(check[0])

    # print("データ抽出期間[",st_time,"~",ed_time,"]")
    # print("サンプルサイズ[",len(diffs),"]")
    # print("---")
    
    if len(diffs) <= 0:
        print("検定可能サンプルなし")
        return -1,-1
    
    return diffs, fname_list

def _get_date_range(st_time, ed_time):

    if (ed_time - st_time).days < 0:
        print("エラー: ed_time は st_time より後の時刻を指定して下さい")
        sys.exit()

    sd = st_time.date()
    day_list = [sd]

    for i in range((ed_time - st_time).days):
        day_list.append(sd + datetime.timedelta(days = i + 1))

    return day_list

def get_params_target(ID, st_time, freq, num, wav_dir, diffs = None, exclusion = False, SN_check = False, direction = "advance"):

    time = st_time

    if diffs == None:
        diffs = []

    # パラメータが指定数になるまでループ処理
    while len(diffs) < num:
        event_time, path = _get_target_event_time(ID, time, wav_dir, direction = direction)
 
        data = wav_load(path)
        sub_data = data[:,0]
        slm_data = data[:,1]

        slm_lv = cal_CPB_level(slm_data,freq)
        sub_lv = cal_CPB_level(sub_data,freq)
        # tex = ", band: {:.4g} Hz , slm: {:.3g} dB , sub: {:.3g} dB ,"

        if SN_check == False or slm_lv > SLM_NOISE_LEVEL[str(freq)] + SNR:
            diffs.append(slm_lv - sub_lv)
        
        if direction == "advance":
            time = event_time + datetime.timedelta(seconds = 1)
        elif direction == "backward":
            time = event_time - datetime.timedelta(seconds = 1)
        else:
            print("引数:directionが間違っています[advanceもしくはbackwardが必要]")

    if exclusion == True:
        check = smirnov_grubbs(np.array(diffs), 0.05)
        # print("除外データ:",check[1],"外れ値個数:",check[1].size)
        diffs = list(check[0])

    if len(diffs) == num:
        # print("データ抽出期間[",st_time,"~",event_time,"]")
        # print("データ数:", num)
        return diffs
    
    return get_params_target(ID, time, freq, num, wav_dir, diffs, exclusion = exclusion, SN_check = SN_check, direction = direction)

def _get_target_event_time(ID, st_time, wav_dir, next = False, direction = "advance"):

    """
    st_timeから過去へ遡り、最も近い騒音イベント時刻を取得する
    探索対象は実音ファイルファイル名
    """

    if next == True and direction == "advance":
        st_time = st_time + datetime.timedelta(days=1)
        st_time = st_time.replace(hour=0, minute=0, second=0)
    elif next == True and direction == "backward":
        st_time = st_time - datetime.timedelta(days=1)
        st_time = st_time.replace(hour=23, minute=59, second=59)
    
    if st_time.date() >= datetime.datetime.now().date() and next == False:
        print("失敗:st_timeは現在日より前の日付を指定して下さい")
        sys.exit()
    elif st_time.date() >= datetime.datetime.now().date() and next == True and direction == "advance":
        print("失敗:必要データ数が集まりませんでした")
        sys.exit()
    elif st_time.date() < datetime.date(2022,12,1) and next == True and direction == "backward":
        print("失敗:必要データ数が集まりませんでした")
        sys.exit()

    target_dir = os.path.join(wav_dir,st_time.strftime('%Y%m'),ID,st_time.strftime('%Y%m%d'))
    
    if os.path.isdir(target_dir) == False:
        print("失敗:対象日のディレクトリが存在しません:",target_dir)
        return _get_target_event_time(ID, st_time, wav_dir, next = True, direction = direction)
    
    wav_list = glob.glob(os.path.join(target_dir,'**','*.WAV'), recursive=True)

    if wav_list == []:
        print("失敗:対象ディレクトリ内にWAVEファイルが存在しません:",target_dir)
        return _get_target_event_time(ID, st_time, wav_dir, next = True, direction = direction)
    
    day_event_time_list = []
    for file in wav_list:
        fname = os.path.splitext(os.path.basename(file))[0]
        day_event_time_list.append(datetime.datetime.strptime(fname, '%y%m%d%H%M%S'))
    wav_list.clear()

    if direction == "advance":
        day_event_time_list = sorted(day_event_time_list,reverse=False)
    elif direction == "backward":
        day_event_time_list = sorted(day_event_time_list,reverse=True)

    # 対象Dファイルから騒音イベント時刻を抜き出して指定時間との差を求める
    for event_time in day_event_time_list:
   
        # print("st:",st_time,", event",event_time)
        if direction == "advance":
            if event_time == st_time or event_time >= st_time:
                path = os.path.join(wav_dir,event_time.strftime('%Y%m'),ID,st_time.strftime('%Y%m%d'),
                                    datetime.datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
                return event_time, path
        elif direction == "backward":
            if event_time == st_time or event_time <= st_time:
                path = os.path.join(wav_dir,event_time.strftime('%Y%m'),ID,st_time.strftime('%Y%m%d'),
                                    datetime.datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
                return event_time, path

    return _get_target_event_time(ID, st_time, wav_dir, next = True, direction = direction)

def draw_hist(a,b,a_int,tolerance):
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

    #plt.axvline(np.mean(b), color='orangered', linestyle='dashed', linewidth=1)
    #plt.axvspan(b_int[0], b_int[1], color="coral",alpha = 0.5)

    if tolerance != 0:
        plt.axvspan(a_int[0] - tolerance, a_int[0], color="lightgreen",alpha = 0.3)
        plt.axvspan(a_int[1], a_int[1] + tolerance, color="lightgreen",alpha = 0.3)

    plt.legend(loc='upper left') 
    
    return fig

def main():

    ######################################################################################
    # 読み込んだデータからsmirnov_grubbs検定で外れ値を除くかどうか
    exclusion = False
    # オクターブバンドレベルのSNRチェック
    SN_check = False
    # データを抽出する期間A 校正した直後の時間を想定
    caliblation_time = datetime.datetime(2022,12,1,0,0,0)
    # 正常信頼区間の推定水準
    p = 0.99
    # 許される平均値のずれ
    tolerance = 1
    # 遡って異常検知を実行する日数
    ret_day = 14
    # 校正後平均化データサイズ
    num = 30
    ######################################################################################

    process_start_time = datetime.datetime.now()

    settings = []
    settings.insert(0,"---異常発生日---")
    settings.insert(0, "騒音計信号SNRチェック処理 = " + str(SN_check))
    settings.insert(0, "外れ値除外処理 = " + str(exclusion))
    settings.insert(0, "騒音計マイク校正後データ サンプルサイズ =  " + str(num))
    settings.insert(0, "騒音計マイク校正完了時刻 " + str(caliblation_time))
    settings.insert(0, "起動時刻 " + str(process_start_time))

    intervalA = dict()
    diffsA = dict()
    for freq in FREQS:
        diffsA[str(freq)] = get_params_target(ID, caliblation_time, freq, num, WAVE_DIR, exclusion = exclusion, SN_check = SN_check)
        intervalA[str(freq)]  = cal_mean_interval(diffsA[str(freq)],p)

    count = 1
    msg_list = []
    error_day_list = []
    while 1:
        day = datetime.datetime.today() - datetime.timedelta(days = count)
        # day = datetime.datetime(2023,7,1) - datetime.timedelta(days = count)
        print(day.date())
        period = [day.replace(hour=0,minute=0,second=0,microsecond=0),day.replace(hour=23,minute=59,second=59,microsecond=0)]
    
        flag = False
        for freq in FREQS:
            diffsB, fname_list  = get_params_period(ID,period[0], period[1], WAVE_DIR, freq, SN_check)

            if diffsB != -1:

                fig_dir = os.path.join(SAVE_DIR,period[0].strftime('%Y%m%d'))
                if not os.path.exists(fig_dir): 
                    os.makedirs(fig_dir)
                
                for i in range(len(diffsB)):
                    jdg = do_valid(intervalA[str(freq)], diffsB[i], tolerance)
                    if jdg == 1 or jdg == 2:
                        msg = fname_list[i] + ", " + str(freq) + " Hz" + ", 判定:" + str(jdg) + ", diff = " + f'{diffsB[i]:.2g}'
                        msg_list.append(msg)
                        flag = True

                fig = draw_hist(diffsA[str(freq)], diffsB, intervalA[str(freq)], tolerance)
                plt.title(period[0].strftime('%Y%m%d') + "_" + str(freq) + "Hz")
                fig.savefig(os.path.join(fig_dir,period[0].strftime('%Y%m%d') + "_" + str(freq) + "Hz.png"))
                plt.close()

        count += 1
        diff = period[0] - caliblation_time

        if flag == True:
            error_day_list.insert(0,period[0].strftime("%Y%m%d"))

        if diff.days < 2 or count > ret_day:
            break

    fname = datetime.datetime.today() - datetime.timedelta(days = 1)

    with open(os.path.join(LOG_DIR,"valid_" + fname.strftime("%Y%m%d")) + ".txt", 'a') as f:
        for msg in settings:
            f.write(msg + "\n")
        for msg in error_day_list:
            f.write(msg + "\n")
        f.write("---以下異常検知した実音データ一覧---" + "\n")
        for msg in msg_list:
            f.write(msg + "\n")

if __name__ == '__main__':
    main()