import argparse
from pathlib import Path
from settings import Settings
from logger import ValidLogger
from winlog import WindowsEventLogger
from learning import Learning
from sensitivity_detecter import SensitiviyDetecter
from failure_detecter import FailureDetecter

import sys
import yaml
from os import path

def main():

    # 引数読込
    parser = argparse.ArgumentParser(description = 'soundvalid prototype application program')
    parser.add_argument('setting_path', type = Path, help = "アプリケーション設定ファイルパス")
    parser.add_argument("-m","--mode", type = str, default = "anomaly_detection", help = "optional 'learning'指定で正常データ保存実行")
    args = parser.parse_args()
    assert args.setting_path.is_file(), f"設定ファイルパスが不正です: {args.setting_path}"
    assert args.mode == "anomaly_detection" or args.mode == "learning", f"実行モード指定が不正です: {args.mode}"

    # ログ保存先のみ先に取得する
    with args.setting_path.open(mode='r', encoding='utf-8') as yml:
        try:
            log_save_directory = Path(yaml.safe_load(yml)['log_save_directory'])
        except Exception as e:
            msg = f"log_save_directoryの取得に失敗、設定ファイルを確認してください[{e}]"
            raise Exception(msg)
    assert path.isdir(log_save_directory),f"log_save_directory:指定パスが存在しません[{log_save_directory}]"

    # アプリケーションロガー
    LOGGER = ValidLogger(log_save_directory)
    # 設定ファイル読込
    settings = Settings(args.setting_path,LOGGER)
    # Windowsイベントログ
    WIN_LOGGER = WindowsEventLogger("soundvalid_prototype",LOGGER)

    if args.mode == "learning":
        LOGGER.app.info("mode learning:正常パラメータ保存モードで実行")
        Learning(settings,LOGGER).fit()
        LOGGER.app.info("実行終了")
    elif args.mode == "anomaly_detection":
        anormaly_msg_list = []
        LOGGER.app.info("異常検知モードで実行")
        # 騒音計マイク感度チェッククラス
        try:
            anormaly_msg_list += SensitiviyDetecter(settings, LOGGER).do_valid()
        except BaseException as e:
            LOGGER.app.error(f"騒音計マイク感度チェック失敗 {e}")
        # 騒音計マイク故障検知クラス 途中
        try:
            anormaly_msg_list += FailureDetecter(settings, LOGGER).do_valid()
        except BaseException as e:
            LOGGER.app.error(f"騒音計マイク故障チェック失敗 {e}")

    # if msg != []:
    # # 異常検知メッセージをwindowsアプリケーションログ出力
    #     logger.app_logger.info(f"{len(msg)}件の異常を検知")
    #     msg.insert(0, "マイク異常検知実験")
    #     winlogger.warning('\n'.join(msg))
    # else:
    #     logger.app_logger.info("異常検知メッセージなし")

# if __name__ == "__main__":
#     try:
#         main()
#         print("soundvalidが正常に終了しました")
#         sys.exit(0)
#     except Exception as e:
#         print(f"soundvalid異常終了:{e}")
#         sys.exit(1)

if __name__ == "__main__":
    main()