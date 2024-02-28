# pythonによるオーディオインターフェース制御検討
masaki tsutsumino 2023/10/11
---

### オーディオインターフェース制御に使えそうなpythonライブラリ
* Pyaudio
  * asioドライバが使えない
  * sounddeviceより使いにくそう
* sounddevice　おすすめ
  * ASIOデバイスをコントロールできる
  * 入出力のチャンネルマッピングが簡単
  * WASAPI、core audioの制御が簡単
  * とにかく書きやすい使いやすい
  * 録音・再生が簡単にできる

## Sounddevaiceの使い方

### リファレンス
https://python-sounddevice.readthedocs.io/en/0.3.15/index.html

### インストール
---
* anaconda
  * conda install -c conda-forge python-sounddevice
* pip
  * python3 -m pip install sounddevice

### 使用時の設定
---
* 使用するサウンドデバイスを指定する
  * sd.query_devices()で使用可能なデバイス一覧および使いたいデバイスのIDを調べる
* 入出力に関するパラメータの設定 主に設定可能なもの
  * sd.default.device     # 使用するデバイスのID
  * sd.default.samplerate # 入出力に使用されるサンプルレート
  * sd.default.channels   # 入出力チャンネル数の数
  * sd.default.dtype      # 入出力に使用されるサンプルのデータ型 defaultはfloat32
  * sd.default.reset()    # 全ての設定をリセット

* 録音・再生の実行時に引数としてその都度指定することも出来る。これらの設定が動的に変わらないような場合はここで設定するのをおすすめする。

### ASIOドライバの設定
---
* ASIO・CoreAudio・WASAPIなど固有のAPIを通じて入出力をコントロールする場合は別途チャンネルマッピングなどの設定が必要。ここではASIOの設定方法を説明する

* 例えば、入力が2チャンネル、出力が4チャンネルのデバイスを使用する場合

```python:asio設定
sd.default.device = 51 # ASIOデバイスのIDを調べて指定する
asio_out = sd.AsioSettings(channel_map = [0,1,2,3])
asio_in = sd.AsioSettings(channel_map = [0,1])
sd.default.extra_settings = (asio_in,asio_out)
```

### 録音
* 録音したデータをnumpy配列に格納する。samplerate, channels, extra_settingsは初期設定されていれば省略可
```python:録音
recdata = sd.rec("録音タップ数", samplerate, channels, extra_settings = asio_in)
```

### リアルタイム処理
* リアルタイムにデータの入出力処理を行いたい場合、以下のクラスで実現できる
  * Stream #　入出力
  * InputStream #入力
  * OutputStream #出力

* streamを定義した後、with文で使用してやることでstart()が自動的に呼び出されて処理を開始できる
* 1つのオーディオデバイスに対して最大1つのストリームを同時に使用することを想定している
* 入出力のデータはNumpy行列に指定したデータ型の数値で格納されるが、生のバッファオブジェクトとして使いたいときはRawStream,RawInputStream,RawOutputStreamを使用する
* 以下パラメータ
  * samplerate　# 入出力に使用されるサンプルレート
  * blocksize  #ストリームコールバック関数に渡されるフレーム数、つまり一回で読み書きするサンプル数。多分わざわざ指定しなくて良い
  * device # 使用するデバイスのID
  * channels　# 入出力チャンネル数の数
  * dtype　# 入出力に使用されるサンプルのデータ型
  * latency # 入出力の遅延時間を秒で指定 省略可
  * extra_settings # ASIOなどの固有apiの設定
  * **callback** # 一回の入出力ごとに呼び出される関数を渡す。コールバック関数にリアルタイムさせたい処理を記述する

#### コールバック関数について
---
* 例えばマイクから受け取った音声データをリアルタイム処理する場合、入出力1回分の録音データ(ndarray)はindataに格納されている。出力はoutdata
* ASIOデバイスで 入力を2チャンネル指定、ブロックサイズ(バッファサイズ)が2048の場合、コールバック関数が一度呼び出されると、indataという変数に(2048,2)サイズの録音データが格納されている。リアルタイム処理はindataに対して行う。
* outputの場合はブロックサイズ分のデータが埋められていないといけない、再生できないので

```python:callback func
# 定義の仕方
callback(indata: ndarray, outdata: ndarray, frames: int、time： CData, status： CallbackFlags)
```

### サンプルプログラム
---
* リアルタイム録音の動作確認のための参考お試しコードを置いておきます
* 堤野のテスト環境で使用したのはベリンガーのUMC ASIO Driverですが、デバイスIDの設定さえ変えればDirect Soundでもなんでも動かせます
* やはり遅延が少ないのでASIOドライバを使うのがよさそうです

* auto_mic_plot_mono.py
  * 参考サイトのコードほぼまんま。
* auto_mic_plot_stereo.py ASIOドライバを使うようにした
  * monoをUMC202HDの2input同時使用するようにした
* auto_mic_plot_hexa.py
  * UMC1820の6input同時使用するようにした
* auto_mic_plot_hexa_OneBoard.py
  * UMC1820の6input同時使用するが、波形の描画は一つのグラフにするように変えた