import argparse
from pathlib import Path
from settings import Settings
from logger import Valid_logger
from winlog import WindowsEventLogger
from learning import Learning
from sensitivity_detecter import Sensitiviy_Detecter

SETTING_PATH = Path(r"D:\Develop\SoundValid\v2.0.0\TestCode\Valid_test13\soundvalid_setting.yaml")

def main():

    # コマンドライン引数の設定
    parser = argparse.ArgumentParser(description = 'マイク異常検知実装テストプログラム13')
    parser.add_argument('setting_path', type = Path, help = "json設定ファイルのファイルパス")
    parser.add_argument("-m","--mode", type = str, default = "anomaly_detection", help = "optional 'learning' を指定すると正常データ算出保存を実行する")
    args = parser.parse_args()
    assert args.setting_path.is_file(), f"設定ファイルパスが不正です: {args.setting_path}"
    assert args.mode == "anomaly_detection" or args.mode == "learning", f"実行モード指定が不正です: {args.mode}"

    # 設定ファイル読込
    settings = Settings(args.setting_path)
    # ロガー生成
    logger = Valid_logger(settings.log_save_directory)
    winlogger = WindowsEventLogger("soundvalid_tester13")

    msg = []
    if args.mode == "learning":
        logger.app_logger.info("正常データ算出保存モードで実行")
        ln = Learning(settings, logger)
        ln.fit()
        ln.save()
        logger.app_logger.info("正常パラメータ算出・保存完了")

    elif args.mode == "anomaly_detection":
        logger.app_logger.info("異常検知モードで実行")
        # 騒音計マイク感度異常検知クラス
        sn = Sensitiviy_Detecter(settings, logger)
        # 正常パラメータ読み込み
        sn.load_normal_parameters()
        # 異常検知実行
        msg += sn.do_valid()

    # 騒音計マイク故障検知クラス
    # an = Anormaly_Detecter(settings, logger)
    # # 正常パラメータ読み込み
    # an.load_normal_parameters()
    # # 異常検知実行
    # msg += an.do_valid()

    # if msg != []:
    # # 異常検知メッセージをwindowsアプリケーションログ出力
    #     logger.app.info(f"{len(msg)}件の異常を検知")
    #     msg.insert(0, "マイク異常検知実験")
    #     winlogger.warning('\n'.join(msg))
    # else:
    #     logger.app.info("異常検知メッセージなし")

if __name__ == "__main__":
    main()