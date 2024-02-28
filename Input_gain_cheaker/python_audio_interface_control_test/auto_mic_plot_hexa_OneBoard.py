#### サンプルプログラム
# リアルタイム収音と波形表示
# サイトのプログラムをほぼそのまま拝借
# UMC202HDを使って2-inputのマイク入力波形を同時にプロットする
# apiにはAsioを使用

"""
https://mori-memo.hateblo.jp/entry/2022/05/14/070650
さっそくリアルタイム収音をやってみましょう。
python-sounddeviceには入出力信号をリアルタイムでnumpy配列として処理できるStreamというクラスが実装されておりますので、これを使えば簡単にリアルタイム処理が書けます。
収音にはInputStreamというクラスを使用します。
下記は10秒間マイクからの入力信号をNumpy配列にしてprintするという処理を行うコードです。
callback関数を作成しておき、その中でリアルタイムに処理したい処理を書きます。
"""

# ライブラリのインポート
import sounddevice as sd
import numpy as np
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt

# Asioデバイスの設定
asio_in = sd.AsioSettings(channel_selectors = [0, 1, 2, 3, 4, 5, 6])

# 変数定義
downsample = 10
fs = 48000 # サンプルレート

sd.default.device = 51          # 使用するデバイスのID
sd.default.samplerate = fs      # 入出力に使用されるサンプルレート
sd.default.channels = 6         # 入出力チャンネル数の数
sd.default.dtype = 'float32'    # 入出力に使用されるサンプルのデータ型 defaultは

fig = plt.figure()
ax = fig.subplots()

length = int(1000 * fs / (1000 * downsample))
plotdata = np.zeros((length,6))

line1, = ax.plot(plotdata[:,0])
line2, = ax.plot(plotdata[:,1])
line3, = ax.plot(plotdata[:,2])
line4, = ax.plot(plotdata[:,3])
line5, = ax.plot(plotdata[:,4])
line6, = ax.plot(plotdata[:,5])

ax.set_ylim([-1.0, 1.0])
ax.set_xlim([0, length])
ax.yaxis.grid(True)
ax.legend(["CH1", "CH2", "CH3", "CH4", "CH5", "CH6"])

fig.tight_layout()

# コールバック関数 リアルタイムに行う処理を記述
def callback(indata, frames, time, status):
    # 再描画するグラフのデータを作成
    global plotdata
    data = indata[::downsample]
    shift = len(data)
    plotdata = np.roll(plotdata, -shift, axis = 0)
    plotdata[-shift:] = data
    sec = (len(indata)/fs) * 1000
    # print(data.shape,indata.shape,f"{sec:.3g}" + "msec")

# sounddeviceでリアルタイム入力を行うクラスを作成
stream = sd.InputStream(
        # channels = 6,
        # dtype ='float32',
        callback = callback
    )

# グラフを再描画する関数
def update_plot(frame):
    global plotdata
    line1.set_ydata(plotdata[:,0])
    line2.set_ydata(plotdata[:,1])
    line3.set_ydata(plotdata[:,2])
    line4.set_ydata(plotdata[:,3])
    line5.set_ydata(plotdata[:,4])
    line6.set_ydata(plotdata[:,5])
    return line1, line2, line3, line4, line5, line6

ani = FuncAnimation(fig, update_plot, interval = 42.7, blit = True)

with stream:
    plt.show()