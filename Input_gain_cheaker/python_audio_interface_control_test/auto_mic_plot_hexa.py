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
ax1 = fig.add_subplot(6, 1, 1) # input1
ax2 = fig.add_subplot(6, 1, 2) # input2
ax3 = fig.add_subplot(6, 1, 3) # input3
ax4 = fig.add_subplot(6, 1, 4) # input4
ax5 = fig.add_subplot(6, 1, 5) # input5
ax6 = fig.add_subplot(6, 1, 6) # input6

length = int(1000 * fs / (1000 * downsample))
plotdata = np.zeros((length,6))

line1, = ax1.plot(plotdata[:,0])
line2, = ax2.plot(plotdata[:,1])
line3, = ax3.plot(plotdata[:,2])
line4, = ax4.plot(plotdata[:,3])
line5, = ax5.plot(plotdata[:,4])
line6, = ax6.plot(plotdata[:,5])

ax1.set_ylim([-1.0, 1.0])
ax2.set_ylim([-1.0, 1.0])
ax3.set_ylim([-1.0, 1.0])
ax4.set_ylim([-1.0, 1.0])
ax5.set_ylim([-1.0, 1.0])
ax6.set_ylim([-1.0, 1.0])

ax1.set_xlim([0, length])
ax2.set_xlim([0, length])
ax3.set_xlim([0, length])
ax4.set_xlim([0, length])
ax5.set_xlim([0, length])
ax6.set_xlim([0, length])

ax1.yaxis.grid(True)
ax2.yaxis.grid(True)
ax3.yaxis.grid(True)
ax4.yaxis.grid(True)
ax5.yaxis.grid(True)
ax6.yaxis.grid(True)

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
    print(data.shape,indata.shape,f"{sec:.3g}" + "msec")

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