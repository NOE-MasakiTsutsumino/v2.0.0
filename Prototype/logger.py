""" encoding utf-8

アプリケーション動作ロギング 分析結果ログ出力クラス
DEBUG       問題探求に必要な詳細な情報を出力したい場合
INFO        想定内の処理が行われた場合
WARNING     想定外の処理やそれが起こりそうな場合
ERROR       重大な問題により、機能を実行出来ない場合
CRITICAL    プログラムが実行不可となるような重大なエラーが発生した場合
"""

# imports
import logging
from pathlib import Path
from datetime import datetime
from os import mkdir, path

# code
class ValidLogger():
    def __init__(self, log_save_directory):
        self.__log_dir = Path(log_save_directory,"log")
        if not path.isdir(self.__log_dir):
            mkdir(self.__log_dir)
        self.app = self.__get_app_logger(logger_name = "app")
        self.app.debug("app_logger instantized")
        self.result = self.__get_result_logger(logger_name = "result")
        self.app.debug("result_logger instantized")
        self.app.debug("instantized")

    # プログラムの実行動作ログハンドラ
    def __get_app_logger(self, logger_name: str):
        logger = logging.getLogger(logger_name)
        # ロギングレベル設定
        logger.setLevel(logging.INFO)
        # ロギングメッセージフォーマット
        formatter = logging.Formatter('%(asctime)s - %(module)s - %(funcName)s - %(levelname)s: %(message)s')
        # コンソール出力ハンドラ追加
        stream_handler = logging.StreamHandler()
        # ロギングメッセージフォーマット設定
        stream_handler.setFormatter(formatter)
        # コンソール出力 ロギングレベル設定
        stream_handler.setLevel(logging.DEBUG)
        # コンソール出力ハンドラ追加
        logger.addHandler(stream_handler)
        # ログファイル名設定
        filename = datetime.now().strftime('%Y%m%d') + "_app.log"
        # ログファイルパス作成
        file = Path(self.log_dir, filename)
        # ログファイル出力設定
        file_handler = logging.FileHandler(file, encoding = 'utf-8')
        # ファイル出力ログレベルを設定
        file_handler.setLevel(logging.INFO)
        # ロギングメッセージフォーマット設定
        file_handler.setFormatter(formatter)
        # ファイル出力ハンドラ追加
        logger.addHandler(file_handler)

        return logger

    # 異常が検知された時に内容を出力するロガー
    def __get_result_logger(self, logger_name: str):
        logger = logging.getLogger(logger_name)
        # ロギングレベル設定
        logger.setLevel(logging.INFO)
        # ログファイル名設定
        filename = datetime.now().strftime('%Y%m%d') + "_result.log"
        # ログファイルパス作成
        file = Path(self.log_dir, filename)
        # ログファイル出力設定
        file_handler = logging.FileHandler(file, encoding = 'utf-8')
        # フファイル出力ハンドラ追加
        logger.addHandler(file_handler)

        return logger

    @property
    def  log_dir(self):
        return self.__log_dir