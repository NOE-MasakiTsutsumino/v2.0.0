""" encoding utf-8

異常検知プロトタイプアプリケーション設定ファイルロードクラス

初期化後の内部変数の状態
        wav_directory                           上書き不可,クラス外参照可
        log_save_directory                      上書き不可,クラス外参照可
        chart_save_directory                    上書き不可,クラス外参照可
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

        self.__AVAILABLE_FREQS = [250,500,1000,2000,4000]
        self.logger = logger

        with setting_file_path.open(mode='r', encoding='utf-8') as yml:
            settings = yaml.safe_load(yml)

        class SettingPath(Settings):
            wav_directory: Path
            log_save_directory: Path
            chart_save_directory: Path

        class SignalProcessSettings(Settings):
            tap: int
            overlap_rate: float
            window: str
            mean_time: float

        class DetectorCommonSettings(Settings):
            system_start_date: str
            return_days: int
            valid_common_calibrated_time: bool
            common_calibrated_time: str
            learning_sample_size: int
            learning_target_freqs: list[int]
            sensitivity_confidence_level: float
            sensitivity_sample_size: int
            sensitivity_reload_limit_size: float
            sensitivity_peak_level_percentile: float
            valid_sensitivity_save_chart: float
            failure_confidence_level: float
            failure_floor_level_percentile: float

        class StationSettings(Settings):
            stationid: str
            stationname: str
            learnig_valid: bool
            calibrated_time: str # Exsample "2022-12-01 00:00:00"
            internal_cal_level: float
            sensitivity_valid: bool
            sensitivity_target_freqency: list[int]
            sensitivity_tolerance: float
            failure_valid: bool
            failure_target_freqency: list[int]
            failure_tolerance: float


        # self.__station_settings = list(settings['station_settings'])
        # self.logger.app.info("アプリケーション設定ファイルロード成功")
        # self.__check_settings_format()
        # self.__check_signal_process_settings_format()
        # self.__check_detector_common_settings_format()
        # self.logger.app.info("アプリケーション設定パラメータフォーマットチェック完了")
        # self.__check_station_settings_format()
        # self.logger.app.info("測定局別設定パラメータフォーマットチェック完了")

        # システム運用開始日時をdatetime型に変換
        self.system_start_date = datetime.strptime(self.system_start_date,'%Y-%m-%d')
        # 全測定局共通の校正完了日時をdatetime型に変換
        if self.__valid_common_calibrated_time:
            self.common_calibrated_time = datetime.strptime(self.common_calibrated_time,'%Y-%m-%d %H:%M:%S')
        self.chart_save_directory = Path(self.chart_save_directory,"fig")

        self.logger.app.debug("instantized")

    def __check_settings_format(self):
        if not path.isdir(self.wav_directory):
            msg = f"wav_directory:指定パスは存在しません[{self.wav_directory}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if not path.isdir(self.log_save_directory):
            msg = f"log_save_directory:指定パスは存在しません[{self.log_save_directory}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if not path.isdir(self.chart_save_directory):
            msg = f"chart_save_directory:指定パスは存在しません。分析画像出力を無効化します[{self.chart_save_directory}]"
            self.valid_sensitivity_save_chart = False
            self.logger.app.error(msg)

    def __check_signal_process_settings_format(self):
        if not self.tap & (self.tap - 1) == 0:
            msg = f"signal_process_settings:tapは2のべき乗の整数を指定して下さい[{self.tap}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if self.overlap_rate < 0.0 or self.overlap_rate >= 1.0:
            msg = f"signal_process_settings:overlap_rateは0.0から0.99の範囲で指定して下さい[{self.overlap_rate}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        try:
            signal.get_window(self.window,1)
        except Exception:
            msg = f"signal_process_settings:window-窓関数の入力値が無効[{self.window}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if self.mean_time < 0.0 or self.mean_time >= 3.0:
            msg = f"signal_process_settings:mean_timeは0.1から3.0の範囲で指定して下さい[{self.mean_time}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)

    def __check_detector_common_settings_format(self):
        try:
            time = datetime.strptime(self.system_start_date, '%Y-%m-%d')
        except Exception as e:
            msg = f"detector_common_settings:system_start_dateの入力値不正[{e}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if time > datetime.now():
            msg = f"detector_common_settings:system_start_dateは現在日より後には設定できません[{time.date()}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if self.return_days < 1 or self.return_days > 100:
            msg = f"detector_common_settings:return_daysは1から100までの整数で指定して下さい[{self.return_days}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if not self.valid_common_calibrated_time in [True,False]:
            msg = f"detector_common_settings:valid_common_calibrated_timeはtrueもしくはfalseで指定して下さい[{self.valid_common_calibrated_time}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        try:
            time = datetime.strptime(self.common_calibrated_time, '%Y-%m-%d %H:%M:%S')
        except Exception as e:
            msg = f"detector_common_settings:common_calibrated_timeの入力値不正[{e}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if time > datetime.now():
            msg = f"detector_common_settings:common_calibrated_timeは現在時刻より後には設定できません[{time}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if self.learning_sample_size < 385 or self.learning_sample_size > 1000:
            msg = f"detector_common_settings:learning_sample_sizeは385から1000までの整数で指定して下さい[{self.learning_sample_size}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        for freq in self.learning_target_freqs:
            if not freq in self.__AVAILABLE_FREQS:
                msg = f"detector_common_settings:learning_target_freqsの入力値不正[{freq}]\n利用可能な周波数一覧:{self.__AVAILABLE_FREQS}"
                self.logger.app.critical(msg)
                raise ValueError(msg)
        if self.sensitivity_confidence_level < 0.90 or self.sensitivity_confidence_level > 0.99:
            msg = f"detector_common_settings:sensitivity_confidence_levelは0.9から0.99までの範囲で指定して下さい[{self.sensitivity_confidence_level}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if self.sensitivity_sample_size < 2 or self.sensitivity_sample_size> 1000:
            msg = f"detector_common_settings:sensitivity_sample_sizeは2から1000までの整数で指定して下さい[{self.sensitivity_sample_size}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if self.sensitivity_reload_limit_size < 0 or self.sensitivity_reload_limit_size > 0.5:
            msg = f"detector_common_settings:sensitivity_reload_limit_sizeは0から0.5までの範囲で指定して下さい[{self.sensitivity_reload_limit_size}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if self.sensitivity_peak_level_percentile < 1 or self.sensitivity_peak_level_percentile > 100:
            msg = f"detector_common_settings:sensitivity_peak_level_percentileは1から100までの範囲で指定して下さい[{self.sensitivity_peak_level_percentile}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if not self.valid_sensitivity_save_chart in [True,False]:
            msg = f"detector_common_settings:valid_sensitivity_save_chartはtrueもしくはfalseで指定して下さい[{self.valid_sensitivity_save_chart}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if self. failure_confidence_level < 0.90 or self. failure_confidence_level > 0.99:
            msg = f"detector_common_settings:failure_confidence_levelは0.9から0.99までの範囲で指定して下さい[{self.failure_confidence_level}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if self.failure_floor_level_percentile < 1 or self.failure_floor_level_percentile > 100:
            msg = f"detector_common_settings:failure_floor_level_percentileは1から100までの範囲で指定して下さい[{self.failure_floor_level_percentile}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)

    def __check_station_settings_format(self):

        station_list = []
        for station in self.station_settings:
            station_list.append(station["stationid"])
        if len(station_list) != len(set(station_list)):
            msg = f"station_settings:設定ファイル内でstationidが重複しています[{station_list}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        for station in self.station_settings:
            if len(str(station["stationid"])) != 4:
                msg = f"station_settings:stationidの文字数不正[{station['stationid']}]"
                self.logger.app.critical(msg)
                raise ValueError(msg)
            if not station["learnig_valid"] in [True,False]:
                msg = f"station_settings:{station['stationid']}:learnig_validはtrueもしくはfalseで指定して下さい[{station['learnig_valid']}]"
                self.logger.app.critical(msg)
                raise ValueError(msg)
            if station["learnig_valid"]:
                if not self.valid_common_calibrated_time:
                    try:
                        time = datetime.strptime(station["calibrated_time"], '%Y-%m-%d %H:%M:%S')
                    except Exception as e:
                        msg = f"station_settings:{station['stationid']}:calibrated_timeの入力値不正[{e}]"
                        self.logger.app.critical(msg)
                        raise ValueError(msg)
                    if time > datetime.now():
                        msg = f"station_settings:{station['stationid']}:calibrated_timeは現在時刻より後には設定できません[{time}]"
                        self.logger.app.critical(msg)
                        raise ValueError(msg)
                    cal = abs(station["internal_cal_level"])
                    decimal_point = str(cal).find(".")
                    if decimal_point == -1:
                        decimal_point = len(str(cal))
                    digit = len(str(cal).split('.')[0])
                    num = int(str(cal)[decimal_point - 1])
                    if num != 4 and num != 3 or digit != 3 :
                        msg = f"station_settings:{station['stationid']}:internal_cal_levelの入力値不正[{station['internal_cal_level']}]"
                        self.logger.app.critical(msg)
                        raise ValueError(msg)
            if not station["sensitivity_valid"] in [True,False]:
                msg = f"station_settings:{station['stationid']}:sensitivity_validはtrueもしくはfalseで指定して下さい[{station['sensitivity_valid']}]"
                self.logger.app.critical(msg)
                raise ValueError(msg)
            if station["sensitivity_valid"]:
                for freq in station["sensitivity_target_freqency"]:
                    if not freq in self.__AVAILABLE_FREQS:
                        msg = f"station_settings:{station['stationid']}:sensitivity_target_freqencyの入力値不正[{freq}]\n利用可能な周波数一覧:{self.__AVAILABLE_FREQS}"
                        self.logger.app.critical(msg)
                        raise ValueError(msg)
                if station["sensitivity_tolerance"] < 0.0 or station["sensitivity_tolerance"] > 1.0:
                    msg = f"station_settings:{station['stationid']}:sensitivity_toleranceは0.0から1.0までの範囲で指定して下さい[{station['sensitivity_tolerance']}]"
                    self.logger.app.critical(msg)
                    raise ValueError(msg)
            if not station["failure_valid"] in [True,False]:
                msg = f"station_settings:{station['stationid']}:failure_validはtrueもしくはfalseで指定して下さい[{station['failure_valid']}]"
                self.logger.app.critical(msg)
                raise ValueError(msg)
            if station["failure_valid"]:
                for freq in station["failure_target_freqency"]:
                    if not freq in self.__AVAILABLE_FREQS:
                        msg = f"station_settings:{station['stationid']}:failure_target_freqencyの入力値不正[{freq}]\n利用可能な周波数一覧:{self.__AVAILABLE_FREQS}"
                        self.logger.app.critical(msg)
                        raise ValueError(msg)
                if station["failure_tolerance"] < 0.0 or station["failure_tolerance"] > 10.0:
                    msg = f"station_settings:{station['stationid']}:failure_toleranceは0.0から10.0までの範囲で指定して下さい[{station['failure_tolerance']}]"
                    self.logger.app.critical(msg)
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
    def valid_sensitivity_save_chart(self):
        return self.__valid_sensitivity_save_chart
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
            self.logger.app.critical(msg)
            raise ValueError(msg)
        self.__system_start_date = time

    @common_calibrated_time.setter
    def common_calibrated_time(self, time):
        if time < self.system_start_date:
            msg = f"common_calibrated_timeはsystem_start_dateより前日に設定できません"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        if time > datetime.now():
            msg = f"common_calibrated_timeは現在時刻より後には設定できません"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        self.__common_calibrated_time = time

    @valid_sensitivity_save_chart.setter
    def valid_sensitivity_save_chart(self, status: bool):
        if not status in [True,False]:
            msg = f"detector_common_settings:valid_sensitivity_save_chartはtrueもしくはfalseの文字列で指定して下さい[{status}]"
            self.logger.app.critical(msg)
            raise ValueError(msg)
        self.__valid_sensitivity_save_chart = status

    @chart_save_directory.setter
    def chart_save_directory(self, path: Path):
        self.__chart_save_directory = path