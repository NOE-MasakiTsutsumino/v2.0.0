from detecter import Detecter
from signals import SignalProcesses
from datetime import datetime, timedelta, time, timedelta
import numpy as np
from math import floor
import save_chart as sc
import os
import glob
from math import modf

class Sensitiviy_Detecter(Detecter):

    """
    騒音計マイク感度異常診断機能クラス
    """

    def __init__(self, settings, logger):

        # 親クラス継承
        super().__init__(settings, logger)
        self.sp = SignalProcesses(settings, logger)

        self.sample_size = settings.sample_size
        self.reload_limit_of_data = settings.reload_limit_of_data
        self.peak_level_percentile = settings.peak_level_percentile

        self.logger.app_logger.info("Sensitiviy_Detecter class instantized")

    def do_valid(self):
        # 異常メッセージ初期化
        msg_list = []
        # 測定局毎にループ
        for stid in self.target_station_list:
            # 異常検知実行
            station_msg = self._do_valid_station(stid)
            if station_msg != []:
                msg_list += station_msg
            self.logger.app_logger.info(f"sensitiviy - {stid} - complete")

        return msg_list

    def _do_valid_station(self, stid):
        """
        測定局別処理 感度異常診断
        """

        # 出力初期化
        msg_list = []

        # 測定局設定読込
        freqs, tolerance_floor, tolerance_upper, cal = self._load_station_settings(stid)

        # 日別処理
        for day in self.target_day_list:

            st_time = datetime.combine(day, time(23,59,59))

            target_dir = os.path.join(self.wav_directory, day.strftime('%Y%m'), stid, day.strftime('%Y%m%d'))

            if os.path.isdir(target_dir):
                file = glob.glob(os.path.join(target_dir,'*.WAV'))
                reload_limit_num = floor(len(file)* self.reload_limit_of_data)
            else:
                msg = f"対象日のディレクトリが存在しません,実行できませんでした:{stid}:{target_dir}"
                self.logger.app_logger.error(msg)
                continue

            # 異常検知メッセージ初期化
            anorm_freqs = []
            # オクターブバンド別処理
            for freq in freqs:
                # 異常検知パラメータ算出
                params = self._get_target_parms(stid, st_time, freq, reload_limit_num)
                if not params:
                    self.logger.app_logger.error(f"{stid} - {day} - {freq} - 感度異常検知を実行できませんでした")
                    self.logger.result.error(f"sensitiviy,{stid},{day},{freq},異常検知不可")
                    continue
                else:
                    # 異常判定
                    jadge = self._jadge_sensivity(cal, stid, freq, params, tolerance_floor, tolerance_upper, day)

                if jadge:
                    anorm_freqs.append(freq)
                    self.logger.result.warning(f"sensitiviy,{stid},{day},{freq},異常あり")
                else:
                    self.logger.result.info(f"sensitiviy,{stid},{day},{freq},異常なし")

                self.logger.app_logger.info(f"sensitiviy_detecter - {stid} - {day} - {freq} - complete")

            # 異常があった場合、メッセージをロギング
            if anorm_freqs != []:
                # メッセージの整理
                msg = "sensitivity-{}-[{}]-{}".format(stid, ",".join(map(str, anorm_freqs)), day)
                msg_list.append(msg)
                # ログ出力
                self.logger.result.warning(msg)

            self.logger.app_logger.info(f"sensitiviy_detecter - {stid} - {day} - complete")

        return msg_list

    def _load_station_settings(self, stid):

        self.target_station_list
        freqs  = self.station_settings["id" == stid]["sensitivity_target_freqency"]
        tolerance = self.station_settings["id" == stid]["sensitivity_tolerance"]

        cal = self.station_settings["id" == stid]["internal_cal_level"]
        decimal, _ = modf(cal)

        decimal_point = str(abs(cal)).find(".")
        if decimal_point == -1:
            decimal_point = len(str(abs(cal)))

        # 指定した桁の数を取得する
        num = int(str(abs(cal))[decimal_point - 1])
        if num == 4:
            tolerance_upper = tolerance  - decimal
            tolerance_floor = (-1 * tolerance) - decimal
        elif num == 3:
            tolerance_upper = tolerance  +   decimal
            tolerance_floor =  (-1*tolerance) - (-1*decimal)

        return freqs, tolerance_floor, tolerance_upper, cal

    def _get_target_parms(self, stid, st_time, freq, reload_limit_num, params = None):
        # データ探索開始日時初期化
        time = st_time
        # 出力初期化
        if params == None:
            params = []

        # 外れデータ棄却カウント数初期化
        reload_count = 0
        # パラメータが指定数になるまでループ処理
        while len(params) < self.sample_size:
            event_time, path = self.get_target_event_time(stid, time, direction = "backward")
            # print(event_time,freq)
            if not event_time:
                self.logger.app_logger.eroor("データを必要数集められませんでした[必要数:{},不足数{}]".format(self.sample_size,self.sample_size - len(params)))
                return False

            fs, data = self.sp.wav_load(path)
            sub_data = data[:,0]
            slm_data = data[:,1]

            oct_mask = self.sp.make_oct_mask(freq, fs)

            # ピーク付近のレベル差
            slm_peak_lv = self.sp.cal_CPB_percentile_level(slm_data, oct_mask, fs, self.peak_level_percentile)

            # 演算失敗チェック
            if not slm_peak_lv:
                self.logger.app_logger.error(f"オクターブバンドレベル算出に失敗")
                return False
            sub_peak_lv = self.sp.cal_CPB_percentile_level(sub_data, oct_mask, fs, self.peak_level_percentile)
            params.append(slm_peak_lv - sub_peak_lv)

            time = event_time - timedelta(seconds = 1)

        params, count = self._delete_outlier_value(stid, freq, params, reload_limit_num)
        reload_count += count

        if count == -1:
            return False

        if reload_count > reload_limit_num:
            self.logger.app_logger.error(f"実音ファイル再読み込み数が上限")
            return False

        if len(params) == self.sample_size:
            return params

        # 自身を再帰
        return self._get_target_parms(stid, time, freq, reload_limit_num, params)

    def _delete_outlier_value(self, stid, freq, params, reload_limit_num):
        count = 0
        while count <= reload_limit_num:
            std = np.std(params, ddof = 1)
            if np.isnan(std):
                msg = f"異常検知パラメータ標準偏差がnan判定、保存された正常パラメータを確認して下さい"
                self.logger.app_logger.warning(msg)
                return params, -1

            if std > self.normal_params[stid]["peak_stdv"][str(freq)]:
                dist = list(np.abs(params - np.mean(params)))
                idx = dist.index(max(dist))
                params.pop(idx)
                count += 1
            else:
                break
        return params, count

    def _jadge_sensivity(self, cal, stid, freq, params, tolerance_floor, tolerance_upper, day):
        """
        感度異常診断実行
        """
        mean = np.mean(params)
        m_lower, m_upper = self.cal_mean_interval(params, self.confidence_level)

        n_lower = self.normal_params[stid]["peak_interval_lower"][str(freq)]
        n_upper = self.normal_params[stid]["peak_interval_upper"][str(freq)]
        sc.draw_sensitivity_histogram(cal, stid, freq, params, mean, m_lower, m_upper, n_lower, n_upper, tolerance_floor, tolerance_upper, self.chart_save_directory, day)

        print(m_lower, m_upper)

        if n_lower + tolerance_floor > m_lower:
            self.logger.app_logger.debug(f"異常 - {freq} - マイク感度低い")
            return True
        elif n_upper + tolerance_upper < m_upper:
            self.logger.app_logger.debug(f"異常 - {freq} - マイク感度高い")
            return True
        else:
            self.logger.app_logger.debug(f"異常なし - {freq}")
            return False