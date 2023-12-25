import logging
from pathlib import Path
from datetime import datetime
from os import mkdir, path

"""
get_app_loggerはプログラム動作記録用のロガー生成
get_result_loggerは検知した異常を記録するロガー生成
"""

class Valid_logger():

    def __init__(self, log_save_directory):

        if not path.isdir(log_save_directory):
            mkdir(log_save_directory)

        self.log_save_directory = log_save_directory
        self.app_logger = self.__get_app_logger(logger_name = "app")
        self.result = self.__get_result_logger(logger_name = "result")

        self.app_logger.debug("logger instantized")

    # プログラムの実行動作確認用ロガー
    def __get_app_logger(self, logger_name: str):

        # ログハンドラをインスタンス化
        logger = logging.getLogger(logger_name)

        # ログレベルをINFO以上に設定
        logger.setLevel(logging.INFO)

        # ログメッセージのフォーマット作成
        formatter = logging.Formatter('%(asctime)s - %(module)s - %(funcName)s - %(levelname)s: %(message)s')

        # console出力ハンドラ
        logger.setLevel(logging.DEBUG)

        # ログをコンソール出力する設定
        stream_handler = logging.StreamHandler()

        # 作成したログメッセージのフォーマットをハンドラに設定
        stream_handler.setFormatter(formatter)

        # コンソール出力するログレベルを設定
        stream_handler.setLevel(logging.DEBUG)

        # コンソール出力ハンドラをロガーに追加
        logger.addHandler(stream_handler)

        # ログファイル名を作成
        filename = datetime.now().strftime('%Y%m%d') + "_app.log"

        # ログファイルパス作成
        file = Path(self.log_save_directory, filename)

        # ログをファイル出力する設定
        file_handler = logging.FileHandler(file, encoding = 'utf-8')

        # ファイル出力するログレベルを設定
        file_handler.setLevel(logging.DEBUG)

        # 作成したログメッセージのフォーマットをハンドラに設定
        file_handler.setFormatter(formatter)

        # ファイル出力ハンドラをロガーに追加
        logger.addHandler(file_handler)

        return logger

    # 異常が検知された時に内容を出力するロガー
    def __get_result_logger(self, logger_name: str):

        # ログハンドラをインスタンス化
        logger = logging.getLogger(logger_name)

        # ログレベルをWARNING以上に設定
        logger.setLevel(logging.INFO)

        # ログファイル名を作成
        filename = datetime.now().strftime('%Y%m%d') + "_result.log"

        # ログファイルパス作成
        file = Path(self.log_save_directory, filename)

        # ログをファイル出力する設定
        file_handler = logging.FileHandler(file, encoding = 'utf-8')

        # ファイル出力ハンドラをロガーに追加
        logger.addHandler(file_handler)

        return logger