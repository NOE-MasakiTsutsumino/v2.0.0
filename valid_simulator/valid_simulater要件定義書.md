# Valid_simulater要件定義

## 1.概要
騒音計マイク感度異常検知のアルゴリズム、つまり異常検知の精度を検証するプログラムを作成する

## 2.要件
* 開発言語はPythonとする

## ４．プログラムの動作
* 指定日、指定測定局の実音ファイルをDドライブから別フォルダにコピー
* コピーした実音ファイルをランダムに選択して読み込み、振幅を操作して異常状態（以後テストデータ）を作り出し、保存
* マイク異常検知テストプログラムValid_testをテストデータに対して実行
* 作り出した異常状態とテストプログラムValid_testで検知された異常を比較して結果を保存し、終了
以上

### 更新履歴
* 2023/10/31　基本的な要件をまとめた 堤野