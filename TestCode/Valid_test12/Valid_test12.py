import argparse
from pathlib import Path
from settings import Settings
from logger import Valid_logger
from detecter import Learning, Anormaly, Sensitiviy

SETTING_PATH = Path(r"D:\Develop\SoundValid\v2.0.0\TestCode\Valid_test12\NORMAL_PARAMETERS.json")

def main():

    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description = 'マイク異常検知実装テストプログラム')
    parser.add_argument('settingpath', type = Path, help = "json設定ファイルのファイルパス")
    args = parser.parse_args()
    assert args.settingpath.is_file(), f"設定ファイルパスが不正です: {args.settingpath}"

    # 設定ファイル読込
    settings = Settings(args.settingpath)

    # ロガー生成
    logger = Valid_logger(settings)

    # 読み込んだ設定ファイルのフォーマットをチェック
    check = Settings.check_settings_format(settings)
    if not check:
        msg = f"設定ファイルの値が不正です({check})"
        logger.app.critical(msg)
        raise Exception(msg)

    # 設定ファイルの情報から異常検知の準備
    ln = Learning(settings, logger)
    normal_params = ln.fit()

    an = Anormaly(settings, logger, normal_params)
    an.do_valid_anormaly()

    sn = Sensitiviy(settings, logger, normal_params)
    sn.do_valid_sensitivity()


if __name__ == "__main__":
    main()