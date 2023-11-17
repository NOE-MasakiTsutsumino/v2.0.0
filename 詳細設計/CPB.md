# cpb.py

## 1.CPB

### 機能
fftの通過帯域合算によるオクターブバンドレベルを算出するためのクラス。以下のメソッドを持つ

* make_oct_mask
* cal_CPB_mean_level
* cal_CPB_percentile_level
---
### 1.クラス初期化メソッド
#### 入力
* settings:設定ファイルオブジェクト
* logger:アプリケーションのログハンドラオブジェクト
---
### 2.make_oct_mask
#### 入力
* center_freq:オクターブバンド中心周波数一個
#### 出力
* oct_mask:オクターブバンドの通過帯域であればtrue、通過帯域外であればfalseの値を持つndarray
---
### 3.cal_CPB_mean_level
#### 入力
* signal:wavファイルの信号データ,モノラルで渡す
* oct_freq_mask:make_oct_maskで作ったオクターブバンドマスク
#### 出力
* 信号データのオクターブバンドレベルパワー平均値
---
### 4.cal_CPB_percentile_level
#### 入力
* signal:wavファイルの信号データ,モノラルで渡す
* oct_freq_mask:make_oct_maskで作ったオクターブバンドマスク
* percent:パーセンタイル
#### 出力
* 信号データのオクターブバンドレベル変動のパーセンタイル値
---
## 変更履歴
2023/11/17 作成 堤野