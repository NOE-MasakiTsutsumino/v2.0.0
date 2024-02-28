#### サンプルプログラム
# リアルタイム収音と波形表示
# サイトのプログラムをほぼそのまま拝借

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

# オーディオ入出力デバイス指定
sd.default.device = [14, 5]

# 変数定義
downsample = 10
fs = 44100

length = int(1000 * fs / (1000 * downsample))
plotdata = np.zeros((length))
fig, ax = plt.subplots()
line, = ax.plot(plotdata)
ax.set_ylim([-1.0, 1.0])
ax.set_xlim([0, length])
ax.yaxis.grid(True)
fig.tight_layout()

# コールバック関数 リアルタイムに行う処理を記述
def callback(indata, frames, time, status):
    # 再描画するグラフのデータを作成
    global plotdata
    data = indata[::downsample, 0]
    shift = len(data)
    plotdata = np.roll(plotdata, -shift, axis=0)
    plotdata[-shift:] = data

# sounddeviceでリアルタイム入力を行うクラスを作成
stream = sd.InputStream(
        channels = 1,
        dtype ='float32',
        callback = callback
    )

# グラフを再描画する関数
def update_plot(frame):
    global plotdata
    line.set_ydata(plotdata)
    return line,

ani = FuncAnimation(fig, update_plot, interval = 26, blit = True)

with stream:
    plt.show()