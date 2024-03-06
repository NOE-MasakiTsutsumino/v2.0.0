# CH53のデータをロバストスケーリング、外れ値除外、yeo-ijonson変換の順で平均値信頼区間を求める
# サンプルサイズは1日の実音データ数とする

from datetime import datetime, timedelta
from pathlib import Path
from os import path
from glob import glob
import pandas as pd
import learning_test_func as ln
from sklearn.preprocessing import RobustScaler, PowerTransformer
import itertools
import numpy as np
from scipy import stats

# 初期設定値

wav_dir = Path(r"D:\Diana\新千歳空港\WAVE") ## WAVEファイルのパス
stid = "CH53"   ## 測定局ID
start_day = datetime(year=2023,month=1,day=1)   ## 校正完了時間
day_range = 500
center_freqs = [250,500,1000,2000]
tap = 1024
percentile = 90
mean_time_sec = 0.1

rb = RobustScaler(with_centering=False,with_scaling=True)
pt = PowerTransformer(method="yeo-johnson",standardize=False,copy=True)

target_day_list = [start_day]
for i in range(day_range):
    target_day_list.append(start_day + timedelta(days = i + 1))

print(f"{start_day}～{start_day + timedelta(days=day_range)}")

ret_columns = ["day","size","250","out_250","500","out_500","1000","out_1000","2000","out_2000"]
ret = pd.DataFrame(columns=ret_columns)
# 対象日ごとにループ
for day in target_day_list:
    wave_file_list = []
    target_dir = path.join(wav_dir, day.strftime('%Y%m'), stid, day.strftime('%Y%m%d'))

    if path.isdir(target_dir):
        wave_file_list += glob(path.join(target_dir,'**','*.WAV'),recursive = True)
    else:
        continue
    if wave_file_list == []:
        continue

    # 異常検知データ算出
    columns = list(map(str,center_freqs))
    dataset = pd.DataFrame(columns=columns)
    for file in wave_file_list:
        fs, signal = ln.wav_load(file)
        oct_freq_masks = ln.make_oct_masks(center_freqs, tap, fs)
        data_list = ln.detect_diff_data(signal, tap, oct_freq_masks, fs, mean_time_sec, percentile)
        dataset = pd.concat([dataset,pd.DataFrame([data_list], columns=columns, dtype="object")], axis=0)

    t_dataset = {f'{freq}': list() for freq in oct_freq_masks.keys()}
    # データ変換と外れ値除外
    record = [day,len(wave_file_list)]
    for freq in oct_freq_masks.keys():

        # ロバストスケーリング
        df = pd.DataFrame(dataset[freq],copy=True)
        rb.fit(df[:])
        df[:] = rb.transform(df[:])
        t_dataset[freq] = list(itertools.chain.from_iterable(df[:].values.tolist()))

        # # 外れ値除外
        t_dataset[freq], out = ln.smirnov_grubbs(list(t_dataset[freq]), 0.05)

        # # yeo変換
        df = pd.DataFrame(t_dataset[freq],copy=True)
        pt.fit(df[:])
        df[:] = pt.transform(df[:])
        t_dataset[freq] = list(itertools.chain.from_iterable(df[:].values.tolist()))

        n = len(t_dataset[freq])
        dof = n-1
        mean = np.mean(t_dataset[freq])
        scale = np.std(t_dataset[freq],ddof=1)/np.sqrt(n)
        data = stats.t(loc=mean, scale=scale, df=dof)
        bottom, upper = data.interval(alpha = 0.95)

        inv_stats = pt.inverse_transform(np.array([mean,bottom,upper]).reshape(-1, 1))
        inv_stats = rb.inverse_transform(inv_stats).reshape(-1)

        record.append(inv_stats[0])
        record.append(len(out))

    ret = pd.concat([ret,pd.DataFrame([record], columns=ret_columns, dtype="object")], axis=0)
    print(day)
ret.to_csv("1日毎の異常検知データ推定平均値.csv")

