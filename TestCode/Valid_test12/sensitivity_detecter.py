from detecter import Detecter
from datetime import datetime, timedelta, time, timedelta
import os
import glob
from signals import SignalProcesses
import numpy as np
from scipy import stats
from math import floor
import json

class Sensitiviy_Detecter(Detecter):

    """
    騒音計マイク感度異常診断機能クラス
    """

    def __init__(self, settings, logger):

        #　親クラス継承
        super().__init__(settings, logger)

        #　閾値取得
        self.co_tolerance  = float(settings.common["sensitivity_tolerance"])
        self.logger.app.debug(f"sensitivity_tolerance:{self.co_tolerance}")

        self.sample_reload_limit_percent_of_day = float(settings.common["sample_reload_limit_percent_of_day"])
        self.logger.app.debug(f"sample_reload_limit_percent_of_day:{self.sample_reload_limit_percent_of_day}")

        self.sample_reload_limit_number = floor(self.normaly_sample_size * self.sample_reload_limit_percent_of_day /100.0)
        self.logger.app.debug(f"ssample_reload_limit_number:{self.sample_reload_limit_number}")

        self.logger.app.info("Sensitiviy_Detecter class instantized")

    def do_valid(self):
        # 異常メッセージ初期化
        msg_list = []
        # 測定局毎にループ
        for stid in self.target_station_list:
            # 異常検知実行
            station_msg = self._do_valid_station(stid)
            if station_msg != []:
                msg_list.append(station_msg)
            self.logger.app.info(f"sensitiviy - {stid} -complete")

        return msg_list

    def _do_valid_station(self, stid):
        """
        測定局別処理 感度異常診断
        """

        # 出力初期化
        msg_list = []

        # 測定局設定読込
        freqs, tolerance = self._load_station_settings(stid)

        # 日別処理
        for day in self.day_list:

            st_time = datetime.combine(day, time(23,59,59))

            # 異常検知メッセージ初期化
            anorm_freqs = []
            # オクターブバンド別処理
            for freq in freqs:
                # 異常検知パラメータ算出
                params = self._get_target_parms(stid, st_time, freq)
                if not params:
                    self.logger.app.error(f"{stid} - {day} - 感度異常検知を実行できませんでした")
                    break
                else:
                    # 異常判定
                    jadge = self._jadge_sensivity(stid, freq, params, tolerance)

                if not jadge:
                    anorm_freqs.append(freq)

            # 異常があった場合、メッセージをロギング
            if anorm_freqs != []:
                # メッセージの整理
                msg = "sensitivity-{}-[{}]-{}".format(stid, ",".join(map(str, anorm_freqs)), day)
                msg_list.append(msg)
                # ログ出力
                self.logger.result.warning(msg)

            self.logger.app.info(f"sensitiviy_detecter - {day} - complete")

        return msg_list

    def _load_station_settings(self, stid):

        if "target_frequency" in self.station_settings["id"==stid]:
            freqs  = self.station_settings["id" == stid]["target_frequency"]
        else:
            freqs = self.co_target_frequency

        if "sensitivity_tolerance" in self.station_settings["id"==stid]:
            t = self.station_settings["id" == stid]["sensitivity_tolerance"]
        else:
            t = self.co_tolerance

        return freqs, t

    def _get_target_parms(self, stid, st_time, freq, params = None):
        # データ探索開始日時初期化
        time = st_time

        # 出力初期化
        if params == None:
            params = []

        # 外れデータ棄却カウント数初期化1
        reload_count = 0
        # パラメータが指定数になるまでループ処理
        while len(params) < self.normaly_sample_size:
            event_time, path = self.get_target_event_time(stid, time, direction = "backward")

            if event_time == False:
                self.logger.app.eroor("データを必要数集められませんでした[必要数:{},不足数{}]".format(self.normaly_sample_size,self.normaly_sample_size - len(params)))
                return False

            signal = self.sp.wav_load(path)
            sub_data = signal[:,0]
            slm_data = signal[:,1]

            # ピーク付近のレベル差
            slm_peak_lv = self.sp.cal_CPB_percentile_level(slm_data, self.sp.oct_freq_mask[str(freq)], 90)
            # 演算失敗チェック
            if not slm_peak_lv:
                self.logger.app.error(f"オクターブバンドレベル算出に失敗")
                return False
            sub_peak_lv = self.sp.cal_CPB_percentile_level(sub_data, self.sp.oct_freq_mask[str(freq)], 90)
            params.append(slm_peak_lv - sub_peak_lv)

            time = event_time - timedelta(seconds = 1)

        params, count = self._delete_outlier_value(stid, freq, params)
        reload_count += count

        if reload_count > self.sample_reload_limit_number:
            return -1

        if len(params) == self.normaly_sample_size:
            return params

        # 自身を再帰
        return self._get_target_parms(stid, time, freq, params)

    def _delete_outlier_value(self, stid, freq, params):
        count = 0
        while count <= self.sample_reload_limit_number:
            var = np.var(params, ddof = 1)
            if var > self.normal_params[stid]["peak_norm_var"][str(freq)]:
                dist = list(np.abs(params - np.mean(params)))
                idx = dist.index(max(dist))
                params.pop(idx)
                count += 1
            else:
                break

        return params, count

    def _jadge_sensivity(self, stid, freq, params, tolerance):
        """
        感度異常診断実行
        """
        mean = np.mean(params)
        # print(self.normal_params[stid]["peak_norm_interval_lower"][str(freq)] - tolerance, mean, self.normal_params[stid]["peak_norm_interval_upper"][str(freq)] + tolerance)
        if self.normal_params[stid]["peak_norm_interval_lower"][str(freq)] - tolerance > mean:
            self.logger.app.debug(f"異常 - {freq} - 低い")
            return False
        elif self.normal_params[stid]["peak_norm_interval_upper"][str(freq)] + tolerance < mean:
            self.logger.app.debug(f"異常 - {freq} - 高い")
            return False
        else:
            self.logger.app.debug(f"異常なし - {freq}")
            return True