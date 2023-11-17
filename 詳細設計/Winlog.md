# winlog.py

## 1.WindowsEventLogger

### 機能
windowsイベントログを出力するログハンドラを生成するクラス

### 1.初期化メソッド
#### 入力
* ロガーの名前
#### 出力
* info,erroer,warningのレベルでwindowsイベントログが出力可能なログハンドラ

### 仕様
* pywin32のインストールが必要
* win32evtlogライブラリの import OpenEventLog, ReportEventメソッドが必要

### 使い方
イベントソースはあらかじめレジストリに登録しておく必要がある。PowerShellで以下のコマンドを実行して登録する
`New-EventLog -LogName Application -Source "ロガーの名前"`

ソースコード内で以下のように書くと使える
`winlogger = WindowsEventLogger("ロガーの名前")`

`winlogger.info("出力するログのメッセージ内容")`
`winlogger.error("出力するログのメッセージ内容")`
`winlogger.warning("出力するログのメッセージ内容")`

## 更新履歴
2023/10/17 作成 堤野