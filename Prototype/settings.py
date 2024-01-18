""" encoding utf-8

異常検知プロトタイプアプリケーション設定ファイルロードクラス

初期化後の内部変数の状態
    signal_process_settings
        tap                                     上書き不可,クラス外参照可
        overlap_rate                            上書き不可,クラス外参照可
        window                                  上書き不可,クラス外参照可
        mean_time                               上書き不可,クラス外参照可
    detector_common_settings
        system_start_date: datetime             条件付き変更可,クラス外参照可
        return_days                             上書き不可,クラス外参照可
        valid_common_calibrated_time            上書き不可,クラス外参照可
        common_calibrated_time: datetime        条件付き変更可,クラス外参照可
        learning_sample_size                    上書き不可,クラス外参照可
        learning_target_freqs                   上書き不可,クラス外参照可
        sensitivity_confidence_level            上書き不可,クラス外参照可
        sensitivity_sample_size                 上書き不可,クラス外参照可
        sensitivity_reload_limit_size           上書き不可,クラス外参照可
        sensitivity_peak_level_percentile       上書き不可,クラス外参照可
        failure_confidence_level                上書き不可,クラス外参照可
        failure_floor_level_percentile          上書き不可,クラス外参照可
    station_settings
        stationid                   上書き不可,クラス外参照可
        name                        上書き不可,クラス外参照可
        learnig_valid               上書き不可,クラス外参照可
        calibrated_time             上書き不可,クラス外参照可
        internal_cal_level          上書き不可,クラス外参照可
        sensitivity_alert           上書き不可,クラス外参照可
        sensitivity_target_freqency 上書き不可,クラス外参照可
        sensitivity_tolerance       上書き不可,クラス外参照可
        failure_target_freqency     上書き不可,クラス外参照可
        failure_tolerance           上書き不可,クラス外参照可
        failure_alert               上書き不可,クラス外参照可
"""

# imports
import yaml
from pathlib import Path
from os import path
from scipy import signal
from datetime import datetime

# code
class Settings(object):

    def __init__(self, setting_file_path: Path, logger):

        with setting_file_path.open(mode='r', encoding='utf-8') as yml:
            settings = yaml.safe_load(yml)

        self.logger = logger

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

        self.__learning_sample_size = int(detector_common_settings["learning_sample_size"])
        self.__learning_target_freqs = list(detector_common_settings["learning_target_freqs"])
        self.__sensitivity_confidence_level = float(detector_common_settings["sensitivity_confidence_level"])
        self.__sensitivity_sample_size = int(detector_common_settings["sensitivity_sample_size"])
        self.__sensitivity_reload_limit_size = float(detector_common_settings["sensitivity_reload_limit_size"])
        self.__sensitivity_peak_level_percentile = float(detector_common_settings["sensitivity_peak_level_percentile"])
        self.__failure_confidence_level = float(detector_common_settings["failure_confidence_level"])
        self.__failure_floor_level_percentile = float(detector_common_settings["failure_floor_level_percentile"])
        self.__station_settings = list(settings['station_settings'])
        logger.app.info("設定ファイルオープン成功")
        self.__check_settings_format()
        self.__check_signal_process_settings_format()
        self.__check_detector_common_settings_format()
        logger.app.info("設定ファイルフォーマットチェック完了")
        self.__check_station_settings()
        logger.app.info("測定局別設定フォーマットチェック完了")

        # システム運用開始日時をdatetime型に変換
        self.system_start_date = datetime.strptime(self.system_start_date,'%Y-%m-%d')
        # 全測定局共通の校正完了日時をdatetime型に変換
        if self.__valid_common_calibrated_time:
            self.common_calibrated_time = datetime.strptime(self.common_calibrated_time,'%Y-%m-%d %H:%M:%S')

    def __check_settings_format(self):
        if not path.isdir(self.wav_directory):
            msg = f"wav_directory:指定パスが無効です{self.wav_directory}"
            self.logger.app.error(msg)
            raise ValueError(msg)
        if not path.isdir(self.log_save_directory):
            msg = f"log_save_directory:指定パスが無効です{self.log_save_directory}"
            self.logger.app.error(msg)
            raise ValueError(msg)
        if not path.isdir(self.chart_save_directory):
            msg = f"chart_save_directory:指定パスが無効です{self.chart_save_directory}"
            self.logger.app.error(msg)
            raise ValueError(msg)

    def __check_signal_process_settings_format(self):
        if not self.tap & (self.tap - 1) == 0:
            msg = f"signal_process_settings:tapは2のべき乗の整数を指定して下さい:入力値={self.tap}"
            self.logger.app.error(msg)
            raise ValueError(msg)
        if self.overlap_rate < 0.0 or self.overlap_rate >= 1.0:
            msg = f"signal_process_settings:overlap_rateは0.0から0.99の範囲で指定して下さい:入力値={self.overlap_rate}"
            self.logger.app.error(msg)
            raise ValueError(msg)
        try:
            signal.get_window(self.window,1)
        except Exception:
            msg = f"窓関数の入力値が無効:{self.window}"
            self.logger.app.error(msg)
            raise ValueError(msg)
        if self.mean_time < 0.0 or self.mean_time >= 3.0:
            msg = f"signal_process_settings:mean_timeは0.1から3.0の範囲で指定して下さい:入力値={self.mean_time}"
            self.logger.app.error(msg)
            raise ValueError(msg)

    def __check_detector_common_settings_format(self):
        try:
            datetime.strptime(self.system_start_date, '%Y-%m-%d')
        except Exception as e:
            msg = f"detector_common_settings:system_start_dateの入力が無効:{e}"
            self.logger.app.error(msg)
            raise ValueError(msg)
        if self.return_days < 1 or self.return_days > 100:
            msg = f"signal_process_settings:mean_timeは1から100までの整数で指定して下さい:入力値={self.return_days}"
            self.logger.app.error(msg)
            raise ValueError(msg)
        if not self.valid_common_calibrated_time in [True,False]:
            msg = f"detector_common_settings:valid_common_calibrated_timeはtrueもしくはfalseの文字列で指定して下さい:入力値={self.valid_common_calibrated_time}"
            self.logger.app.error(msg)
            raise ValueError(msg)
        try:
            datetime.strptime(self.common_calibrated_time, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            msg = f"detector_common_settings:common_calibrated_timeの入力が無効:{e}"
            self.logger.app.error(msg)
            raise ValueError(msg)

    def __check_station_settings(self):
        AVAILABLE_FREQS = [250,500,1000,2000,4000]

        station_list = []
        for station in self.station_settings:
            station_list.append(station["stationid"])
        if len(station_list) != len(set(station_list)):
            msg = f"station_settings:stationidが重複しています:{station_list}"
            self.logger.app.error(msg)
            raise ValueError(msg)
        for station in self.station_settings:
            if len(str(station["stationid"])) != 4:
                msg = f"station_settings:stationidの文字数が不正です:{station['stationid']}"
                self.logger.app.error(msg)
                raise ValueError(msg)
            if not station["learnig_valid"] in [True,False]:
                msg = f"{station['stationid']}:learnig_validはtrueもしくはfalseの文字列で指定して下さい:入力値={station['learnig_valid']}"
                self.logger.app.error(msg)
                raise ValueError(msg)
            if station["learnig_valid"]:
                if self.valid_common_calibrated_time:
                    try:
                        datetime.strptime(station["calibrated_time"], '%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        msg = f"{station['stationid']}:calibrated_timeの入力が無効:{e}"
                        self.logger.app.error(msg)
                        raise ValueError(msg)
                    cal = abs(station["internal_cal_level"])
                    decimal_point = str(cal).find(".")
                    if decimal_point == -1:
                        decimal_point = len(str(cal))
                    digit = len(str(cal).split('.')[0])
                    num = int(str(cal)[decimal_point - 1])
                    if num != 4 and num != 3 or digit != 3 :
                        msg = f"{station['stationid']}:internal_cal_levelの入力が異常?:{station['internal_cal_level']}"
                        self.logger.app.error(msg)
                        raise ValueError(msg)
            if not station["sensitivity_valid"] in [True,False]:
                msg = f"{station['stationid']}:sensitivity_validはtrueもしくはfalseの文字列で指定して下さい:入力値={station['sensitivity_valid']}"
                self.logger.app.error(msg)
                raise ValueError(msg)
            if station["sensitivity_valid"]:
                for freq in station["sensitivity_target_freqency"]:
                    if not freq in AVAILABLE_FREQS:
                        msg = f"{station['stationid']}:sensitivity_target_freqency:無効な周波数です[{freq}]\n利用可能な周波数一覧:{AVAILABLE_FREQS}"
                        self.logger.app.error(msg)
                        raise ValueError(msg)
                if station["sensitivity_tolerance"] < 0.0 or station["sensitivity_tolerance"] > 1.0:
                    msg = f"{station['stationid']}:sensitivity_toleranceは0.0から1.0までの範囲で指定して下さい:入力値={station['sensitivity_tolerance']}"
                    self.logger.app.error(msg)
                    raise ValueError(msg)
            if not station["failure_valid"] in [True,False]:
                msg = f"{station['stationid']}:failure_validはtrueもしくはfalseの文字列で指定して下さい:入力値={station['failure_valid']}"
                self.logger.app.error(msg)
                raise ValueError(msg)
            if station["failure_valid"]:
                for freq in station["failure_target_freqency"]:
                    if not freq in AVAILABLE_FREQS:
                        msg = f"{station['stationid']}:failure_target_freqency:無効な周波数です[{freq}]\n利用可能な周波数一覧:{AVAILABLE_FREQS}"
                        self.logger.app.error(msg)
                        raise ValueError(msg)
                if station["failure_tolerance"] < 0.0 or station["failure_tolerance"] > 10.0:
                    msg = f"{station['stationid']}:failure_toleranceは0.0から10.0までの範囲で指定して下さい:入力値={station['failure_tolerance']}"
                    self.logger.app.error(msg)
                    raise ValueError(msg)

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
    def learning_sample_size(self):
        return self.__learning_sample_size
    @property
    def learning_target_freqs(self):
        return self.__learning_target_freqs
    @property
    def sensitivity_confidence_level(self):
        return self.__sensitivity_confidence_level
    @property
    def sensitivity_sample_size(self):
        return self.__sensitivity_sample_size
    @property
    def sensitivity_reload_limit_size(self):
        return self.__sensitivity_reload_limit_size
    @property
    def sensitivity_peak_level_percentile(self):
        return self.__sensitivity_peak_level_percentile
    @property
    def failure_confidence_level(self):
        return self.__failure_confidence_level
    @property
    def failure_floor_level_percentile(self):
        return self.__failure_floor_level_percentile
    @property
    def station_settings(self):
        return self.__station_settings

    @system_start_date.setter
    def system_start_date(self, time):
        if time > datetime.now():
            msg = f"system_start_dateは現在日より後には設定できません"
            self.logger.app.error(msg)
            raise ValueError(msg)
        self.__system_start_date = time

    @common_calibrated_time.setter
    def common_calibrated_time(self, time):
        if time < self.system_start_date:
            msg = f"common_calibrated_timeはsystem_start_dateより前日に設定できません"
            self.logger.app.error(msg)
            raise ValueError(msg)
        if time > datetime.now():
            msg = f"common_calibrated_timeは現在時刻より後には設定できません"
            self.logger.app.error(msg)
            raise ValueError(msg)
        self.__common_calibrated_time = time