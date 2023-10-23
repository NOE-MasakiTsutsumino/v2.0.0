import argparse
from pathlib import Path
from settings import Settings
from logger import Valid_logger
from learning import Learning

SETTING_PATH = Path(r"D:\Develop\SoundValid\v2.0.0\TestCode\Valid_test12\NORMAL_PARAMETERS.json")

def main():

    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description = 'マイク異常検知テストプログラム12 正常パラメータ算出')
    parser.add_argument('settingpath', type = Path, help = "json設定ファイルのファイルパス")

    # コマンドライン引数解析
    args = parser.parse_args()

    # 設定ファイルが存在しない場合、エラー終了
    assert args.settingpath.is_file(), f"設定ファイルパスが不正です: {args.settingpath}"

    # 設定ファイル読込
    settings = Settings(args.settingpath)

    # ログ出力準備
    logger = Valid_logger(settings)

    # 読み込んだ設定ファイルのフォーマットをチェック
    check = Settings.check_settings_format(settings)
    if not check:
        logger.app.critical(f"設定ファイルの値が不正です({check})")

    # 正常パラメータ算出準備
    ln = Learning(settings, logger)

    # 正常パラメータ算出
    ln.fit()
    logger.app.info("正常パラメータ算出完了")

    # 正常パラメータ保存とバックアップ
    ln.save()
    logger.app.info("正常パラメータ保存完了")

if __name__ == "__main__":
    main()