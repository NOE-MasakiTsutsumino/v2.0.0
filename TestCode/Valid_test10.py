# -*- conding:UTF-8 -*-

"""
Valid_test10.py
2023/07/13 masaki tsutsumino 作成

処理手順

test8とtest9の機能を結合したやつ。感度の低下検知検知とマイクの故障・異常の判定、二つの機能を併せ持つ
"""

import datetime
from pathlib import Path
import numpy as np
import wave
from scipy.io import wavfile
import os
import glob
import sys
import matplotlib.pyplot as plt
from scipy import stats
import psutil

# submic_ch = 0 , slm_ch = 1

ID = "CH53"
DATA_DIR = Path(r"D:\Diana\新千歳空港\DATA")
# WAVE_DIR = Path(r"D:\Diana\Program\SoundValid\workspace\testcode\感度低下検知検証\TEST_WAVE")
WAVE_DIR = Path(r"D:\Diana\新千歳空港\WAVE")
SAVE_DIR = Path(r"D:\Diana\Program\SoundValid\workspace\testcode\感度低下検知検証\TEST_FIG")
LOG_DIR = Path(r"D:\Diana\Program\SoundValid\workspace\testcode\感度低下検知検証\TEST_LOG")
SNR = 10
# FREQS = [125,250,500,1000,2000,4000]

SLM_NOISE_LEVEL = {
    "125":  30,
    "250":  30,
    "500":  30,
    "1000": 30,
    "2000": 30,
    "4000": 30
}

NORMAL_VAR_LIST = {
    "125":  0.311511916,
    "250":  0.028249417,
    "500":  0.028831924,
    "1000": 0.045135937,
    "2000": 0.086729841,
    "4000": 0.070618166
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

def do_valid_anormaly(intervalA, data, tolerance):
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

def do_valid_sensivity(diffsA, diffsB, p, tolerance):
    """
    異常検知の実行
    """

    intervalA = cal_mean_interval(diffsA,p)
    intervalB = cal_mean_interval(diffsB,p)

    # if intervalA[0] - tolerance > intervalB[1]:
    #     jdg = 1
    #     return jdg ,intervalA ,intervalB
    # elif intervalA[1] + tolerance < intervalB[0]:
    #     jdg = 2
    #     return jdg ,intervalA ,intervalB

    if intervalA[0] - tolerance > np.mean(diffsB):
        jdg = 1
        return jdg ,intervalA ,intervalB
    elif intervalA[1] + tolerance < np.mean(diffsB):
        jdg = 2
        return jdg ,intervalA ,intervalB

    return 0, intervalA, intervalB

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

def get_params_target(ID, st_time, freq, num, wav_dir, diffs = None, exclusion = False, SN_check = False, var_check = False ,direction = "advance"):

    time = st_time

    if diffs == None:
        diffs = []

    # パラメータが指定数になるまでループ処理
    while len(diffs) < num:
        event_time, path = _get_target_event_time(ID, time, wav_dir, direction = direction)

        if event_time == -1:
            return -1
 
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
    
    if var_check == True:
        diffs = delete_outlier_var(diffs,freq)
            
    if len(diffs) == num:
        # print("データ抽出期間[",st_time,"~",event_time,"]")
        # print("データ数:", num)
        return diffs
    
    return get_params_target(ID, time, freq, num, wav_dir, diffs, exclusion = exclusion, SN_check = SN_check, var_check = var_check, direction = direction)

def delete_outlier_var(data,freq):
    while 1:
        var = np.var(data,ddof=1)

        if var > NORMAL_VAR_LIST[str(freq)]:
            dist = list(np.abs(data - np.mean(data)))
            idx = dist.index(max(dist))
            data.pop(idx)
        else:
            break

    return data

def _get_target_event_time(ID, st_time, wav_dir, next = False, direction = "advance"):

    """
    st_timeから未来、過去へ遡り、最も近い騒音イベント時刻を取得する
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
        return -1,-1
    elif st_time.date() < datetime.date(2022,12,1) and next == True and direction == "backward":
        print("失敗:必要データ数が集まりませんでした")
        return -1,-1

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

def draw_hist(a,b,a_int,b_int,tolerance):
    """
    結果分析用のヒストグラム画像オブジェクトを作るよ
    """

    dof_a = len(a) -1
    mean_a = np.mean(a)
    scale_a = np.std(a)
    var_a = np.var(a,ddof=1)

    dof_b = len(b) -1
    mean_b = np.mean(b)
    scale_b = np.std(b)
    var_b = np.var(b,ddof=1)

    x_a = np.linspace(start= mean_a-scale_a*5, stop = mean_a + scale_a*5, num=251)
    density_a = stats.t.pdf(x=x_a, df=dof_a, loc=mean_a, scale=scale_a)

    x_b = np.linspace(start= mean_b-scale_b*5, stop = mean_b + scale_b*5, num=251)
    density_b = stats.t.pdf(x=x_b, df=dof_b, loc=mean_b, scale=scale_b)

    fig = plt.figure()
    ax = fig.add_subplot(1, 1, 1)
    plt.hist(a,alpha = 0.5, label='Calibrated [var = ' + str(f'{var_a:.2g}') + "]",bins = 10)
    plt.hist(b,alpha = 0.5, label='Target [var = ' + str(f'{var_b:.2g}') + "]",bins = 10)

    plt.plot(x_a, density_a, color='blue') # 折れ線グラフ
    plt.plot(x_b, density_b, color='orangered') # 折れ線グラフ

    plt.axvline(np.mean(a), color='blue', linestyle='dashed', linewidth=1)
    plt.axvspan(a_int[0], a_int[1], color="skyblue",alpha = 0.3)

    plt.axvline(np.mean(b), color='orangered', linestyle='dashed', linewidth=1)
    # plt.axvspan(b_int[0], b_int[1], color="coral",alpha = 0.5)

    if tolerance != 0:
        plt.axvspan(a_int[0] - tolerance, a_int[0], color="lightgreen",alpha = 0.3)
        plt.axvspan(a_int[1], a_int[1] + tolerance, color="lightgreen",alpha = 0.3)

    plt.legend(loc='upper left') 
    plt.text(0.5,-0.1, "[mean_diff = " + str(f'{mean_b-mean_a:.2g}') + "]",horizontalalignment="center",transform=ax.transAxes)
    
    return fig

def main():

    # 騒音計マイク校正が完了した時刻
    caliblation_time = datetime.datetime(2022,12,1,0,0,0)

    # 分析対象オクターブバンド
    anomaly_freqs       = [500,1000,2000]               # 異常検知
    sensitivity_freqs   = [125,250,500,1000,2000,4000]  # 感度低下検知 

    # 平均信頼区間の推定水準
    anomaly_p       = 0.99  # 異常検知
    sensitivity_p   = 0.95  # 感度低下検知 

    # 許される平均値のずれ[dB]
    anomaly_tolerance       = 1.0   # 異常検知
    sensitivity_tolerance   = 0.5   # 感度低下検知

    # 呼び出すサンプルサイズ
    normal_num: int         = 30    # 騒音計マイク校正後の正常区間算出
    sensitivity_num: int    = 30    # 感度低下検知

    # 遡って異常検知を実行する日数
    recurse_days: int = 1

    #オプション もしかしたら有用かもしれない程度なので基本FalseでOK
    exclusion = False   # 読み込んだデータからsmirnov_grubbs検定で外れ値を除くかどうか
    SN_check = False    # 騒音計オクターブバンドレベルの自己ノイズとのSNRチェック

    #! start↓

    # スクリプトの起動時刻
    process_start_time = datetime.datetime.now()

    start_day = process_start_time.date() - datetime.timedelta(days = 1)
    log_header = []
    log_header.append("プログラム起動時刻 " + str(process_start_time))
    log_header.append("騒音計マイク 前回校正完了時刻 " + str(caliblation_time))

    end_day = start_day - datetime.timedelta(days = recurse_days - 1)
    if end_day < caliblation_time.date():
        end_day = caliblation_time.date() + datetime.timedelta(days = 1)
    log_header.append("異常検知実行日 [" + end_day.strftime("%Y%m%d") + " ~ " + start_day.strftime("%Y%m%d") + "]")

    log_header.append("騒音計マイク校正後 利用サンプルサイズ =  " + str(normal_num))
    log_header.append("異常検知分析対象オクターブバンド = " + str(anomaly_freqs))
    log_header.append("感度低下分析対象オクターブバンド = " + str(sensitivity_freqs))
    log_header.append("騒音計信号SNRチェック = " + str(SN_check))
    log_header.append("外れ値除外処理 = " + str(exclusion))
    log_header.append("---以下検知した異常一覧---")

    log_file_path = os.path.join(LOG_DIR,"valid_" + start_day.strftime("%Y%m%d")) + ".txt"
    with open(log_file_path, 'a') as f:
        for msg in log_header:
            f.write(msg + "\n")
    log_header.clear()

    target_day_list: list = [start_day]
    for i in range((start_day - end_day).days):
        target_day_list.append(start_day - datetime.timedelta(days = i + 1))

    # 異常検知_正常区間算出
    interval_norm = dict()
    diffs_norm = dict()
    for freq in sensitivity_freqs:
        diffs_norm[str(freq)] = get_params_target(ID, caliblation_time, freq, normal_num, WAVE_DIR, exclusion = exclusion, SN_check = SN_check)
        interval_norm[str(freq)]  = cal_mean_interval(diffs_norm[str(freq)], anomaly_p)
        NORMAL_VAR_LIST[str(freq)] = np.var(diffs_norm[str(freq)], ddof = 1)

    count = 1
    while 1:
        mem = psutil.virtual_memory() 
        print(mem.used)

        sensivity_msg_list = []
        anomaly_msg_list = []
        day = datetime.datetime.today() - datetime.timedelta(days = count)
        day_end = day.replace(hour=23,minute=59,second=59,microsecond=0)
        day_st = day.replace(hour=0,minute=0,second=0,microsecond=0)
        print(day.date())
        
        fig_dir = os.path.join(SAVE_DIR,day.strftime('%Y%m%d'))
        if not os.path.exists(fig_dir): 
            os.makedirs(fig_dir)

        for freq in sensitivity_freqs:
            diffs_sens = get_params_target(ID, day_end, freq, sensitivity_num, WAVE_DIR, exclusion = exclusion, SN_check = SN_check, var_check = True, direction = "backward")

            if diffs_sens != -1:
                jdg ,intervalA ,intervalB = do_valid_sensivity(diffs_norm[str(freq)], diffs_sens, sensitivity_p, sensitivity_tolerance)
                if  jdg == 1:
                    msg = day.strftime('%Y%m%d') + " " + str(freq) + " Hz"  + " 騒音計感度低い"
                    sensivity_msg_list.append(msg)
                elif jdg == 2:
                    msg = day.strftime('%Y%m%d') + " " + str(freq) + " Hz" + " 騒音計感度高い"
                    sensivity_msg_list.append(msg)
        
                fig = draw_hist(diffs_norm[str(freq)], diffs_sens, intervalA, intervalB, sensitivity_tolerance)
                plt.title(day.strftime('%Y%m%d') + "_" + str(freq) + "Hz")
                fig.savefig(os.path.join(fig_dir,day.strftime('%Y%m%d') + "_" + str(freq) + "Hz.png"))
                plt.close()
            else:
                anomaly_msg_list.append(str(ID) + ":" + day.strftime('%Y%m%d') + "_データの抽出に失敗,感度低下検知できない")

        for freq in anomaly_freqs:
            diffs_ano, fname_list  = get_params_period(ID, day_st, day_end, WAVE_DIR, freq)

            if diffs_ano != -1:
                for i in range(len(diffs_ano)):
                    jdg = do_valid_anormaly(interval_norm[str(freq)], diffs_ano[i], anomaly_tolerance)
                    if jdg == 1 or jdg == 2:
                        msg = fname_list[i] + ", " + str(freq) + " Hz" + ", 判定:" + str(jdg) + ", diff = " + f'{diffs_ano[i]:.2g}'
                        anomaly_msg_list.append(msg)
            else:
                anomaly_msg_list.append(str(ID) + ":" + day.strftime('%Y%m%d') + "_WAVEファイルが存在しません,anormaly検知できない")

        if sensivity_msg_list != [] or anomaly_msg_list != []:
            with open(log_file_path, 'a') as f:
                for msg in sensivity_msg_list:
                    f.write(msg + "\n")
                for msg in anomaly_msg_list:
                    f.write(msg + "\n")

        count += 1
        diff = day - caliblation_time

        if diff.days < 2 or count > recurse_days:
            break
        
if __name__ == '__main__':
    main()