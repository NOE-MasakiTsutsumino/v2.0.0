from detecter import Detecter
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

        # 共通の校正完了時刻を使用する場合の設定
        self.use_common_calibrated_time = bool(settings.common["use_common_calibrated_time"])
        if 'common_calibrated_time' in settings.common.keys() and self.use_common_calibrated_time == True:
            self.common_calibrated_time = datetime.strptime(settings.common['common_calibrated_time'], '%Y-%m-%d %H:%M:%S')

        self.co_propotion = float(settings.common['propotion'])

        self.logger.app.debug("Learning class instantized")

    def _get_normal_params_freq(self, stid, st_time, freq, proportion) -> tuple:

        """
        オクターブバンドの正常パラメータ(L10とL90それぞれについて)を求める
        """

        time = st_time
        mean_diffs = []
        peak_diffs = []
        floor_diffs = []

        # パラメータが指定数になるまでループ処理
        while len(mean_diffs) < self.normaly_sample_size:

            event_time, path = self.get_target_event_time(stid, time)

            if event_time == -1:
                msg = "失敗:校正完了時刻以降の実音ファイルが不足しています[必要数:{},不足数{}]".format(self.normaly_sample_size,self.normaly_sample_size - len(diffs))
                self.logger.app.error(msg)
                return False

            data = self.sp.wav_load(path)
            sub_data = data[:,0]
            slm_data = data[:,1]

            slm_mean_lv = self.sp.cal_CPB_mean_level(slm_data, self.sp.oct_freq_mask[str(freq)])

            # 演算失敗チェック
            if not slm_mean_lv:
                self.logger.app.info(f"オクターブバンドレベル算出に失敗したためデータ棄却:{path}")
                time = event_time + timedelta(seconds = 1)
                continue

            slm_peak_lv = self.sp.cal_CPB_percentile_level(slm_data, self.sp.oct_freq_mask[str(freq)], 90)
            slm_floor_lv = self.sp.cal_CPB_percentile_level(slm_data, self.sp.oct_freq_mask[str(freq)], 10)

            sub_mean_lv = self.sp.cal_CPB_mean_level(sub_data, self.sp.oct_freq_mask[str(freq)])
            sub_peak_lv = self.sp.cal_CPB_percentile_level(sub_data, self.sp.oct_freq_mask[str(freq)], 90)
            sub_floor_lv = self.sp.cal_CPB_percentile_level(sub_data, self.sp.oct_freq_mask[str(freq)], 10)

            mean_diffs.append(slm_mean_lv - sub_mean_lv)
            peak_diffs.append(slm_peak_lv - sub_peak_lv)
            floor_diffs.append(slm_floor_lv - sub_floor_lv)

            time = event_time + timedelta(seconds = 1)

        m_var = np.var(mean_diffs, ddof = 1)
        p_var = np.var(peak_diffs, ddof = 1)
        f_var = np.var(floor_diffs, ddof = 1)
        var = [m_var, p_var, f_var]

        m_bottom, m_up = self.cal_mean_interval(mean_diffs, proportion)
        p_bottom, p_up = self.cal_mean_interval(peak_diffs, proportion)
        f_bottom, f_up = self.cal_mean_interval(floor_diffs, proportion)
        bottom = [m_bottom, p_bottom, f_bottom]
        up = [m_up, p_up, f_up]

        # 成功
        return var, bottom, up

    def _cal_normal_params_function(self, stid, calibrated_time, freqs, propation) -> dict:

        # 初期化
        ret = {}

        # レベル平均のパラメータ初期化
        ret["mean_norm_var"] = {}
        ret["mean_norm_interval_upper"] = {}
        ret["mean_norm_interval_lower"] = {}

        # ピークレベル程度のパラメータ初期化
        ret["peak_norm_var"] = {}
        ret["peak_norm_interval_upper"] = {}
        ret["peak_norm_interval_lower"] = {}

        # 暗騒音レベル程度のパラメータ初期化
        ret["floor_norm_var"] = {}
        ret["floor_norm_interval_upper"] = {}
        ret["floor_norm_interval_lower"] = {}

        # 対象オクターブバンドごとに算出
        for freq in freqs:
            var, bottom, up = self._get_normal_params_freq(stid, calibrated_time, freq, propation)

            ret["mean_norm_var"][str(freq)] = var[0]
            ret["mean_norm_interval_lower"][str(freq)] = bottom[0]
            ret["mean_norm_interval_upper"][str(freq)] = up[0]

            ret["peak_norm_var"][str(freq)] = var[1]
            ret["peak_norm_interval_lower"][str(freq)] = bottom[1]
            ret["peak_norm_interval_upper"][str(freq)] = up[1]

            ret["floor_norm_var"][str(freq)] = var[2]
            ret["floor_norm_interval_lower"][str(freq)] = bottom[2]
            ret["floor_norm_interval_upper"][str(freq)] = up[2]

        return ret

    def _load_station_settings(self, stid):

        """
        正常パラメータ算出に関する設定を読み込む
        """

        # 共通の校正完了時間を使うが有効になっている場合
        if self.use_common_calibrated_time == True:
            ct = self.common_calibrated_time
        else:
            ct = self.station_settings["id"==stid]["calibrated_time"]
            ct = datetime.strptime(ct, '%Y-%m-%d %H:%M:%S')

        # 対象のオクターブバンド周波数リストを読み込み
        if "target_frequency" in self.station_settings["id"==stid]:
            freqs  = self.station_settings["id" == stid]["target_frequency"]
        else:
            freqs = self.co_target_frequency

        #信頼平均区間の係数読み込み
        if "propotion" in self.station_settings["id"==stid]:
            p = self.station_settings["id" == stid]["propotion"]
        else:
            p = self.co_propotion

        return ct, freqs, p

    def fit(self):

        # 正常パラメータ初期化
        self.norm = {}

        # 測定局ごとにループ処理
        for stid in self.target_station_list:
            # 測定局の設定読み込み
            ct, freqs, p = self._load_station_settings(stid)
            # 測定局の正常パラメータ算出
            temp = self._cal_normal_params_function(stid, ct, freqs ,p)
            if temp != False:
                self.norm[stid] = temp
                self.logger.app.debug("Normal parameter calculation completed - {}".format(stid))

        self.logger.app.debug("learning complete")

        return self.norm

    def save(self, buckup = True):

        filename = "NORMAL_PARAMETERS.json"
        if buckup and os.path.isfile(filename):
            today = datetime.today()
            bk_fname = f"backup_{datetime.strftime(today, '%Y%m%d')}_" + filename
            shutil.copyfile(filename, bk_fname)
            self.logger.app.debug(f"backup file {bk_fname}")

        with open(filename, 'w') as f:
            json.dump(self.norm, f, indent= 2 )
            self.logger.app.debug(f"save NORMAL_PARAMETERS file")

        return True