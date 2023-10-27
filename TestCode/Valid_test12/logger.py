import logging
from pathlib import Path
from datetime import datetime
import os

"""
get_app_loggerはプログラム動作記録用のロガー
get_result_loggerは検知した異常を記録するロガー
"""

class Valid_logger():

    def __init__(self, settings):

        if not os.path.isdir(settings.log_save_dir):
            os.mkdir(settings.log_save_dir)

        self.log_save_dir = settings.log_save_dir
        self.app = self.get_app_logger(self.log_save_dir)
        self.result = self.get_result_logger(self.log_save_dir)

        self.app.debug("logger instantized")

    @classmethod
    # プログラムの実行動作確認用ロガー
    def get_app_logger(cls, save_dir):

        # ログハンドラをインスタンス化
        logger = logging.getLogger("app")

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
        stream_handler.setLevel(logging.INFO)

        # コンソール出力ハンドラをロガーに追加
        logger.addHandler(stream_handler)

        # ログファイル名を作成
        filename = datetime.now().strftime('%Y%m%d') + "_app.log"

        # ログファイルパス作成
        file = Path(save_dir,filename)

        # ログをファイル出力する設定
        file_handler = logging.FileHandler(file, encoding='utf-8')

        # ファイル出力するログレベルを設定
        file_handler.setLevel(logging.INFO)

        # 作成したログメッセージのフォーマットをハンドラに設定
        file_handler.setFormatter(formatter)

        # ファイル出力ハンドラをロガーに追加
        logger.addHandler(file_handler)

        return logger

    @classmethod
    # 異常が検知された時に内容を出力するロガー
    def get_result_logger(cls, save_dir):

        # ログハンドラをインスタンス化
        logger = logging.getLogger("result")

        # ログレベルをWARNING以上に設定
        logger.setLevel(logging.WARNING)

        # ログファイル名を作成
        filename = datetime.now().strftime('%Y%m%d') + "_result.log"

        # ログファイルパス作成
        file = Path(save_dir, filename)

        # ログをファイル出力する設定
        file_handler = logging.FileHandler(file, encoding = 'utf-8')

        # ファイル出力ハンドラをロガーに追加
        logger.addHandler(file_handler)

        return logger