""" UTF-8 """

""" imports """
import yaml
from pathlib import Path
from os import path

""" code """
class Settings(object):

    def __init__(self, settings_path: Path):

        # 設定ファイル読込
        with settings_path.open(mode='r', encoding='utf-8') as yml:
            settings = yaml.safe_load(yml)

        self.__wav_directory = Path(settings['wav_directory'])
        self.__log_save_directory = Path(settings['log_save_directory'])
        self.__chart_save_directory = Path(settings['chart_save_directory'])

        signal_process_settings = dict(settings['signal_process_settings'])
        self.__tap = int(signal_process_settings["tap"])
        self.__overlap_rate = float(signal_process_settings["overlap_rate"])
        self.__window = str(signal_process_settings["window"])
        self.__mean_time = float(signal_process_settings["mean_time"])

        detector_common_settings = dict(settings['detector_common_settings'])
        self.__system_start_date = str(detector_common_settings["system_start_date"])
        self.__return_days = int(detector_common_settings["return_days"])
        self.__valid_common_calibrated_time = bool(detector_common_settings["valid_common_calibrated_time"])
        self.__common_calibrated_time = str(detector_common_settings["common_calibrated_time"])

        self.__lows_confidence_level = float(detector_common_settings["lows_confidence_level"])
        self.__sensitivity_confidence_level = float(detector_common_settings["sensitivity_confidence_level"])

        self.__sample_size = int(detector_common_settings["sample_size"])
        self.__reload_limit_of_data = float(detector_common_settings["reload_limit_of_data"])
        self.__learning_target_freqs = list(detector_common_settings["learning_target_freqs"])
        self.__peak_level_percentile = float(detector_common_settings["peak_level_percentile"])
        self.__floor_level_percentile = float(detector_common_settings["floor_level_percentile"])

        self.__station_settings = list(settings['station_settings'])

    def check_settings_format(self):

        if not path.isdir(self.__wav_directory):
            raise ValueError("指定のWAVEファイルパスが存在しません")

        if not path.isdir(self.__log_save_directory):
            raise ValueError("指定のパスが存在しません")

        if not path.isdir(self.__chart_save_directory):
            raise ValueError("指定のパスが存在しません")

    @property
    def  wav_directory(self):
        return self.__wav_directory

    @property
    def  log_save_directory(self):
        return self.__log_save_directory

    @property
    def  chart_save_directory(self):
        return self.__chart_save_directory

    @property
    def tap(self):
        return self.__tap

    @property
    def overlap_rate(self):
        return self.__overlap_rate

    @property
    def window(self):
        return self.__window

    @property
    def mean_time(self):
        return self.__mean_time

    @property
    def system_start_date(self):
        return self.__system_start_date

    @property
    def return_days(self):
        return self.__return_days

    @property
    def valid_common_calibrated_time(self):
        return self.__valid_common_calibrated_time

    @property
    def common_calibrated_time(self):
        return self.__common_calibrated_time

    @property
    def lows_confidence_level(self):
        return self.__lows_confidence_level

    @property
    def sensitivity_confidence_level(self):
        return self.__sensitivity_confidence_level

    @property
    def sample_size(self):
        return self.__sample_size

    @property
    def reload_limit_of_data(self):
        return self.__reload_limit_of_data

    @property
    def learning_target_freqs(self):
        return self.__learning_target_freqs

    @property
    def station_settings(self):
        return self.__station_settings

    @property
    def peak_level_percentile(self):
        return self.__peak_level_percentile

    @property
    def floor_level_percentile(self):
        return self.__floor_level_percentile