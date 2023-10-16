import logging
from pathlib import Path
from datetime import datetime
import os

class Valid_logger():


    def __init__(self, settings):

        if not os.path.isdir(settings.log_save_dir):
            os.mkdir(settings.log_save_dir)
            print(settings.log_save_dir)

        self.log_save_dir = settings.log_save_dir
        self.app = self.get_app_logger(self.log_save_dir)
        self.result = self.get_result_logger(self.log_save_dir)


    @classmethod
    def get_app_logger(cls, save_dir):
        logger = logging.getLogger("app")
        logger.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(module)s - %(funcName)s- %(levelname)s: %(message)s')

        # console出力ハンドラ
        logger.setLevel(logging.DEBUG)
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        logger.addHandler(stream_handler)

        # ファイル出力ハンドラ
        filename = datetime.now().strftime('%Y%m%d') + "_app.log"
        file = Path(save_dir,filename)
        file_handler = logging.FileHandler(file, encoding='utf-8')
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        return logger


    @classmethod
    def get_result_logger(cls, save_dir):

        logger = logging.getLogger("result")
        logger.setLevel(logging.INFO)
        filename = datetime.now().strftime('%Y%m%d') + "_result.log"
        file = Path(save_dir, filename)
        file_handler = logging.FileHandler(file, encoding = 'utf-8')
        logger.addHandler(file_handler)

        return logger