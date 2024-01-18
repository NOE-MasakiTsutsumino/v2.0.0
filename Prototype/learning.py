""" encoding utf-8

異常検知用統計パラメータ算出保存クラス
"""
# imports
# from signals import SignalProcesses
from detecter import Detecter
from datetime import datetime, timedelta, timedelta
import numpy as np
import json
import os
import shutil
from matplotlib import pyplot as plt
import seaborn as sns
import pandas as pd

# code
class Learning(Detecter):

    def __init__(self, settings, logger):
        super().__init__(settings, logger)
        self.logger.app.debug("instantized")

    def fit(self):
        # 統計パラメータ初期化
        # self.norm = {}
        # 実行対象測定局リスト作成
        target_station_list = self._get_target_station_list(self.settings,"learnig_valid")
        print(target_station_list)
        # 測定局ごとにループ処理
        # for stid in self.target_station_list:

        #     # 測定局の最終校正完了日時
        #     if self.valid_common_calibrated_time:
        #         calibrated_time = self.common_calibrated_time
        #     else:
        #         calibrated_time = self.station_settings["id" == stid]["calibrated_time"]
        #         calibrated_time = datetime.strptime(calibrated_time, '%Y-%m-%d %H:%M:%S')

        #     params = self.__cal_normal_params_function(stid, calibrated_time)

        #     if params:
        #         self.norm[stid] = params
        #         self.logger.app_logger.debug(f"Normal parameter calculation completed - {stid}")

        # self.logger.app_logger.debug("learning complete")

        # return self.norm

    def save(self, buckup = True):

        filename = "NORMAL_PARAMETERS.json"
        if buckup and os.path.isfile(filename):
            today = datetime.today()
            bk_fname = f"backup_{datetime.strftime(today, '%Y%m%d')}_" + filename
            shutil.copyfile(filename, bk_fname)
            self.logger.app_logger.debug(f"backup file {bk_fname}")

        with open(filename, 'w') as f:
            json.dump(self.norm, f, indent = 2 )
            self.logger.app_logger.debug(f"save NORMAL_PARAMETERS file")

        return True

    def __cal_normal_params_function(self, stid, calibrated_time) -> dict:

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
        for freq in self.learning_target_freqs:
            stdv, bottom, up = self.__get_normal_params_freq(stid, calibrated_time, freq)

            ret["peak_stdv"][str(freq)] = stdv[0]
            ret["peak_interval_lower"][str(freq)] = bottom[1]
            ret["peak_interval_upper"][str(freq)] = up[1]

            ret["floor_stdv"][str(freq)] = stdv[1]
            ret["floor_interval_lower"][str(freq)] = bottom[0]
            ret["floor_interval_upper"][str(freq)] = up[0]

        return ret

    def __get_normal_params_freq(self, stid, start_time, freq) -> tuple:

        """
        オクターブバンドの正常パラメータを求める
        """

        time = start_time
        mean_diffs = []
        peak_diffs = []
        floor_diffs = []

        # パラメータが指定数になるまでループ処理
        while len(mean_diffs) < self.sample_size:

            event_time, path = self.get_target_event_time(stid, time)

            if not event_time:
                msg = "失敗:校正完了時刻以降の実音ファイルが不足しています[必要数:{},不足数{}]".format(self.sample_size,self.sample_size - len(mean_diffs))
                self.logger.app_logger.error(msg)
                return False

            fs, data = self.sp.wav_load(path)
            sub_data = data[:,0]
            slm_data = data[:,1]

            oct_mask = self.sp.make_oct_mask(freq, fs)

            slm_mean_lv = self.sp.cal_CPB_mean_level(slm_data, oct_mask)

            # 演算失敗チェック
            if not slm_mean_lv:
                self.logger.app_logger.info(f"オクターブバンドレベル算出に失敗したためデータ棄却:{path}")
                time = event_time + timedelta(seconds = 1)
                continue

            slm_peak_lv = self.sp.cal_CPB_percentile_level(slm_data, oct_mask, fs, self.peak_level_percentile)
            slm_floor_lv = self.sp.cal_CPB_percentile_level(slm_data, oct_mask, fs, self.floor_level_percentile)

            sub_mean_lv = self.sp.cal_CPB_mean_level(sub_data, oct_mask)
            sub_peak_lv = self.sp.cal_CPB_percentile_level(sub_data, oct_mask, fs, self.peak_level_percentile)
            sub_floor_lv = self.sp.cal_CPB_percentile_level(sub_data, oct_mask, fs, self.floor_level_percentile)

            mean_diffs.append(slm_mean_lv - sub_mean_lv)
            peak_diffs.append(slm_peak_lv - sub_peak_lv)
            floor_diffs.append(slm_floor_lv - sub_floor_lv)

            time = event_time + timedelta(seconds = 1)

        mean_diffs = self.pop_outlier_iqr(mean_diffs)
        peak_diffs = self.pop_outlier_iqr(peak_diffs)
        floor_diffs = self.pop_outlier_iqr(floor_diffs)

        p_stdv = np.std(peak_diffs, ddof=1)
        f_stdv = np.std(floor_diffs, ddof=1)
        stdv = [p_stdv, f_stdv]

        # lows正常データ
        lw_f_lower, lw_f_upper = self.cal_mean_interval(floor_diffs, self.confidence_level)

        # sensitivity正常データ
        sn_p_lower, sn_p_upper = self.cal_mean_interval(peak_diffs, self.sensitivity_confidence_level)

        lower = [lw_f_lower, sn_p_lower]
        up = [lw_f_upper, sn_p_upper]

        # 成功
        return stdv, lower, up

    def pop_outlier_iqr(self, data):

        data = pd.Series(data)

        q1 = data.quantile(0.25)
        q3 = data.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr

        ret = data[(data >= lower) & (data <= upper)]
        ret.reset_index(drop=True,inplace=True)

        return ret