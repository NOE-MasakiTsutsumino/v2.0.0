""" encoding utf-8

異常検知用統計パラメータ算出保存クラス
"""
# imports
from signals import SignalProcesses
from detecter import Detecter
from datetime import datetime, timedelta, timedelta
import numpy as np
import json
import os
import shutil
import pandas as pd
from save_chart import plot_histogram_learning_parameters
from matplotlib import pyplot as plt

# code
class Learning(Detecter):

    def __init__(self, settings, logger):
        super().__init__(settings, logger)
        self.sp = SignalProcesses(settings, logger)
        self.logger.app.debug("instantized")

    def fit(self):
        # 統計パラメータ初期化
        normal_parameters = {}
        # 実行対象測定局リスト作成
        target_station_list = self._get_target_station_list(self.settings,"learnig_valid")
        if not target_station_list:
            msg = f"実行対象の測定局がありません、終了します"
            self.logger.app.info(msg)
            return True
        # 測定局ごとにループ処理
        for stationid in target_station_list:
            # 測定局の最終校正完了日時
            if self.settings.valid_common_calibrated_time:
                calibrated_time = self.settings.common_calibrated_time
            else:
                calibrated_time = datetime.strptime(self.settings.station_settings["stationid"==stationid]["calibrated_time"], '%Y-%m-%d %H:%M:%S')
            try:
                station_normal_parameters = self.__get_normal_parameters_station(stationid, calibrated_time)
            except Exception as e:
                msg = f"{stationid}:正常パラメータ算出失敗-{e}"
                self.logger.app.error(msg)
                continue
            if station_normal_parameters:
                normal_parameters[stationid] = station_normal_parameters
                self.logger.app.info(f"{stationid}:正常パラメータ算出成功")
        self.logger.app.info("正常パラメータ算出処理終了")
        try:
            self.__save(normal_parameters,target_station_list,buckup=True)
        except Exception as e:
            msg = f"正常パラメータファイル出力失敗[{e}]"

        return normal_parameters

    def __get_normal_parameters_station(self, stationid, calibrated_time) -> dict:
        # 初期化
        ret = {}
        # ピークレベル程度のパラメータ初期化
        ret["peak_stdv"] = {}
        ret["peak_interval_lower"] = {}
        ret["peak_interval_upper"] = {}
        # 暗騒音レベル程度のパラメータ初期化
        ret["floor_stdv"] = {}
        ret["floor_interval_lower"] = {}
        ret["floor_interval_upper"] = {}
        # 対象オクターブバンドごとに算出
        for freq in self.settings.learning_target_freqs:
            try:
                stdv, bottom, up = self.__get_normal_parameters_freq(stationid, calibrated_time, freq)
            except Exception as e:
                msg = f"{freq}Hz-{e}]"
                raise Exception(msg)
            ret["peak_stdv"][str(freq)] = stdv[0]
            ret["peak_interval_lower"][str(freq)] = bottom[1]
            ret["peak_interval_upper"][str(freq)] = up[1]
            ret["floor_stdv"][str(freq)] = stdv[1]
            ret["floor_interval_lower"][str(freq)] = bottom[0]
            ret["floor_interval_upper"][str(freq)] = up[0]

        return ret

    def __get_normal_parameters_freq(self, stationid, start_time, freq) -> tuple:
        time = start_time
        peak_diffs=[]
        floor_diffs=[]
        while len(peak_diffs) < self.settings.learning_sample_size:
            event_time, path = self._get_target_event_time(stationid, time)
            if not event_time:
                msg = f"校正完了時刻以降の実音ファイルが不足しています(必要数:{self.settings.learning_sample_size},不足数{self.settings.learning_sample_size - len(peak_diffs)})"
                raise Exception(msg)
            fs, data = self.sp.wav_load(path)
            sub_data = data[:,0]
            slm_data = data[:,1]
            oct_mask = self.sp.make_oct_mask(freq, fs)
            try:
                slm_peak_lv = self.sp.cal_CPB_percentile_level(slm_data, oct_mask, fs, self.settings.sensitivity_peak_level_percentile)
                slm_floor_lv = self.sp.cal_CPB_percentile_level(slm_data, oct_mask, fs, self.settings.failure_floor_level_percentile)
                sub_peak_lv = self.sp.cal_CPB_percentile_level(sub_data, oct_mask, fs, self.settings.sensitivity_peak_level_percentile)
                sub_floor_lv = self.sp.cal_CPB_percentile_level(sub_data, oct_mask, fs, self.settings.failure_floor_level_percentile)
            except Exception as e:
                self.logger.app.error(f"{path}:オクターブバンドレベル算出に失敗したためデータ棄却-{e}")
                time = event_time + timedelta(seconds = 1)
                continue
            peak_diffs.append(slm_peak_lv-sub_peak_lv)
            floor_diffs.append(slm_floor_lv-sub_floor_lv)
            time = event_time + timedelta(seconds = 1)

        while(1):
            fig = plot_histogram_learning_parameters(peak_diffs,stationid,freq,"peak_diffs")
            plt.show(block=False)
            jdg = input("Do you want to perform outlier exclusion by quantiles? y/n\n")
            if jdg == "y":
                peak_diffs = self.__pop_outlier_iqr(peak_diffs)
                plt.close()
                break
            elif jdg == "n":
                plt.close()
                break
            else:
                print("Enter 'y' or 'n'\n")
                plt.close()

        while(1):
            fig = plot_histogram_learning_parameters(floor_diffs,stationid,freq,"floor_diffs")
            plt.show(block=False)
            jdg = input("Do you want to perform outlier exclusion by quantiles? y/n\n")
            if jdg == "y":
                floor_diffs = self.__pop_outlier_iqr(floor_diffs)
                plt.close()
                break
            elif jdg == "n":
                plt.close()
                break
            else:
                print("Enter 'y' or 'n'\n")
                plt.close()

        peak_stdv = np.std(peak_diffs, ddof=1)
        floor_stdv = np.std(floor_diffs, ddof=1)
        stdv = [peak_stdv, floor_stdv]
        failure_floor_lower, failure_floor_upper = self._cal_mean_interval(floor_diffs, self.settings.failure_confidence_level)
        sensitivity_peak_lower, sensitivity_peak_upper = self._cal_mean_interval(peak_diffs, self.settings.sensitivity_confidence_level)
        lower = [failure_floor_lower, sensitivity_peak_lower]
        up = [failure_floor_upper, sensitivity_peak_upper]

        self.logger.app.info(f"{stationid}-{freq}-正常パラメータ算出成功")
        return stdv, lower, up

    def __save(self, normal_parameters, target_station_list, buckup = True):
        filename = "NORMAL_PARAMETERS.json"

        # 正常パラメータヘッダー書き込み
        normal_parameters["conditions"] = {}
        normal_parameters["conditions"]["learning_sample_size"] = self.settings.learning_sample_size
        normal_parameters["conditions"]["sensitivity_confidence_level"] = self.settings.sensitivity_confidence_level
        normal_parameters["conditions"]["failure_confidence_level"] = self.settings.failure_confidence_level
        if self.settings.valid_common_calibrated_time:
            normal_parameters["conditions"]["common_calibrated_time"] = self.settings.common_calibrated_time.strftime('%Y-%m-%d %H:%M:%S')
        else:
            normal_parameters["conditions"]["calibrated_time"]={}
            for stationid in target_station_list:
                normal_parameters["conditions"]["calibrated_time"][stationid] = self.settings.station_settings["stationid"==stationid]["calibrated_time"]
        if buckup and os.path.isfile(filename):
            today = datetime.today()
            bk_fname = f"backup_{datetime.strftime(today, '%Y%m%d')}_" + filename
            shutil.copyfile(filename, bk_fname)
            self.logger.app.info(f"正常パラメータファイルバックアップ成功:{bk_fname}:")
        try:
            with open(filename, 'w') as f:
                json.dump(normal_parameters,f,indent=2)
        except Exception as e:
            msg = f"正常パラメータバックアップファイル作成失敗[{e}]"
            self.logger.app.warning(msg)
            raise Exception(msg)
        self.logger.app.info(f"正常パラメータファイル作成成功:{filename}")
        return True

    def __pop_outlier_iqr(self, data):
        data = pd.Series(data)
        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        ret = data[(data >= lower) & (data <= upper)]
        ret.reset_index(drop=True,inplace=True)

        return ret