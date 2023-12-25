from detecter import Detecter
from signals import SignalProcesses
from datetime import datetime, timedelta, timedelta
import numpy as np
import json
import os
import shutil

class Learning(Detecter):

    """
    正常データを算出してjsonファイルで出力するクラス
    """

    def __init__(self, settings, logger):
        super().__init__(settings, logger)
        self.sp = SignalProcesses(settings, logger)

        self.confidence_level = settings.confidence_level
        self.sample_size = settings.sample_size
        self.peak_level_percentile = settings.peak_level_percentile
        self.floor_level_percentile = settings.floor_level_percentile
        self.learning_target_freqs = settings.learning_target_freqs

        # 全測定局共通の校正完了時刻を使用する場合の設定
        self.valid_common_calibrated_time = settings.valid_common_calibrated_time
        if self.valid_common_calibrated_time:
            try:
                self.common_calibrated_time = datetime.strptime(settings.common_calibrated_time, '%Y-%m-%d %H:%M:%S')
            except KeyError as e:
                self.logger.app_logger.error(f"設定ファイルにcommon_calibrated_timeがありません")
                raise e

        self.logger.app_logger.debug("Learning class instantized")

    def fit(self):

        # 正常パラメータ初期化
        self.norm = {}

        # 測定局ごとにループ処理
        for stid in self.target_station_list:

            # 測定局の最終校正完了日時
            if self.valid_common_calibrated_time:
                calibrated_time = self.common_calibrated_time
            else:
                calibrated_time = self.station_settings["id" == stid]["calibrated_time"]
                calibrated_time = datetime.strptime(calibrated_time, '%Y-%m-%d %H:%M:%S')

            params = self.__cal_normal_params_function(stid, calibrated_time)

            if params:
                self.norm[stid] = params
                self.logger.app_logger.debug(f"Normal parameter calculation completed - {stid}")

        self.logger.app_logger.debug("learning complete")

        return self.norm

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

        # レベル平均のパラメータ初期化
        ret["mean_stdv"] = {}
        ret["mean_interval_upper"] = {}
        ret["mean_interval_lower"] = {}

        # ピークレベル程度のパラメータ初期化
        ret["peak_stdv"] = {}
        ret["peak_interval_upper"] = {}
        ret["peak_interval_lower"] = {}

        # 暗騒音レベル程度のパラメータ初期化
        ret["floor_stdv"] = {}
        ret["floor_interval_upper"] = {}
        ret["floor_interval_lower"] = {}

        # 対象オクターブバンドごとに算出
        for freq in self.learning_target_freqs:
            stdv, bottom, up = self.__get_normal_params_freq(stid, calibrated_time, freq)

            ret["mean_stdv"][str(freq)] = stdv[0]
            ret["mean_interval_lower"][str(freq)] = bottom[0]
            ret["mean_interval_upper"][str(freq)] = up[0]

            ret["peak_stdv"][str(freq)] = stdv[1]
            ret["peak_interval_lower"][str(freq)] = bottom[1]
            ret["peak_interval_upper"][str(freq)] = up[1]

            ret["floor_stdv"][str(freq)] = stdv[2]
            ret["floor_interval_lower"][str(freq)] = bottom[2]
            ret["floor_interval_upper"][str(freq)] = up[2]

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

        m_stdv = np.std(mean_diffs, ddof=1)
        p_stdv = np.std(peak_diffs, ddof=1)
        f_stdv = np.std(floor_diffs, ddof=1)
        stdv = [m_stdv, p_stdv, f_stdv]

        m_bottom, m_up = self.cal_mean_interval(mean_diffs, self.confidence_level)
        p_bottom, p_up = self.cal_mean_interval(peak_diffs, self.confidence_level)
        f_bottom, f_up = self.cal_mean_interval(floor_diffs, self.confidence_level)
        bottom = [m_bottom, p_bottom, f_bottom]
        up = [m_up, p_up, f_up]

        # 成功
        return stdv, bottom, up
