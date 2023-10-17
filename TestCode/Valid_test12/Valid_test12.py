import argparse
from pathlib import Path
from settings import Settings
from logger import Valid_logger
from anormaly_detecter import Anormaly_Detecter
from sensitivity_detecter import Sensitiviy_Detecter
SETTING_PATH = Path(r"D:\Develop\SoundValid\v2.0.0\TestCode\Valid_test12\valid_test12_settings.json")

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

    # 騒音計マイク故障検知クラス
    an = Anormaly_Detecter(settings, logger)
    # 正常パラメータ読み込み
    an.load_normal_parameters()
    # 異常検知実行
    an.do_valid()

    # 騒音計マイク感度異常検知クラス
    sn = Sensitiviy_Detecter(settings, logger)
    # 正常パラメータ読み込み
    sn.load_normal_parameters()
    # 異常検知実行
    msg = sn.do_valid()


if __name__ == "__main__":
    main()