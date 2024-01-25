# encoding utf-8

# imports
from detecter import Detecter
from signals import SignalProcesses
from datetime import datetime, timedelta, time, timedelta
import numpy as np
from math import floor
import save_chart as sc
import os
import glob
from math import modf

# code
class SensitiviyDetecter(Detecter):

    def __init__(self, settings, logger):
        super().__init__(settings, logger)
        self.sp = SignalProcesses(settings, logger)
        self.logger.app.debug("instantized")

    def do_valid(self):
        # 異常メッセージ初期化
        anormaly_msg_list = []
        # 実行対象測定局リスト作成
        target_station_list = self._get_target_station_list(self.settings,"sensitivity_valid")
        if not target_station_list:
            msg = f"実行対象の測定局がありません、終了します"
            raise BaseException(msg)
        # 正常パラメータ読み込み
        try:
            self.normal_parameters = self._load_normal_parameters_file()
        except Exception as e:
            self.logger.app.error(f"正常パラメータ読み込み失敗、終了します{e}")
            raise BaseException(e)
        # 測定局毎にループ
        for stationid in target_station_list:
            # 異常検知実行
            station_msg = self._do_valid_station(stationid)
            if station_msg != []:
                anormaly_msg_list += station_msg

        return anormaly_msg_list

    def _do_valid_station(self, stationid):
        # 出力初期化
        msg_list = []
        # 測定局設定読込
        target_freqs, tolerance_floor, tolerance_upper, cal = self._load_station_settings(stationid)
        # 日別処理
        for day in self.target_day_list:
            target_dir = os.path.join(self.settings.wav_directory, day.strftime('%Y%m'), stationid, day.strftime('%Y%m%d'))
            try:
                day_wav_file_list = glob.glob(os.path.join(target_dir,'*.WAV'))
                if len(day_wav_file_list) <= 1:
                    msg = f"{stationid}-{day}:対象日付フォルダ内にWAVファイルが2つ以上ありません、分析失敗"
                    self.logger.app.error(msg)
                    continue
            except Exception as e:
                msg = f"{stationid}-{day}:WAVファイルリストの取得に失敗しました[{e}]"
                self.logger.app.error(msg)
                continue
            # 異常検知メッセージ初期化
            anormaly_freqs = []
            # オクターブバンド別分析
            for freq in target_freqs:
                try:
                    params = self._get_target_parms_freq(stationid, day, day_wav_file_list, freq)
                except Exception as e:
                    self.logger.app.error(f"{freq}Hz-{e}]")
                    continue
                # 異常判定
                try:
                    jadge = self._jadge_sensivity(cal, stationid, freq, params, tolerance_floor, tolerance_upper, day)
                except Exception as e:
                    self.logger.app.error(f"{freq}Hz-異常判定失敗-{e}")
                    continue
                if jadge:
                    anormaly_freqs.append(freq)
                    self.logger.app.debug(f"{stationid}-{day}-{freq}Hz-異常あり")
                else:
                    self.logger.app.debug(f"{stationid}-{day}-{freq}Hz,異常なし")
                self.logger.app.info(f"{stationid}-{day}-{freq}Hz:感度チェック分析成功")
            # 異常があった場合、メッセージをロギング
            if anormaly_freqs != []:
                # メッセージの整理
                msg = "{}:騒音計感度チェック閾値超過[{}]-{}".format(stationid, ",".join(map(str, anormaly_freqs)), day)
                msg_list.append(msg)
                # 分析結果ログ出力
                self.logger.result.warning(msg)
            self.logger.app.debug(f"{stationid}-{day}:感度チェック分析終了")
            if msg_list == []:
                self.logger.result.info(f"{stationid}-{day}-マイク感度チェック異常なし")
                self.logger.app.info(f"{stationid}-{day}-マイク感度チェック異常なし")
        return msg_list

    def _load_station_settings(self, stationid):
        target_freqs  = self.settings.station_settings["stationid" == stationid]["sensitivity_target_freqency"]
        tolerance = self.settings.station_settings["stationid" == stationid]["sensitivity_tolerance"]
        cal = self.settings.station_settings["stationid" == stationid]["internal_cal_level"]
        decimal, _ = modf(cal)
        decimal_point = str(abs(cal)).find(".")
        if decimal_point == -1:
            decimal_point = len(str(abs(cal)))
        num = int(str(abs(cal))[decimal_point - 1])
        if num == 4:
            tolerance_lower = (-1*tolerance) + decimal
            tolerance_upper = tolerance
            # tolerance_upper = tolerance + decimal
        elif num == 3:
            tolerance_lower = tolerance
            tolerance_upper = tolerance - (1-decimal)
            # tolerance_lower =  (-1*tolerance) - (1-decimal)
        if tolerance_lower > 0:
            tolerance_lower = 0.0
        elif tolerance_upper < 0:
            tolerance_upper = 0.0
        self.logger.app.debug(f"{stationid}:感度チェック分析パラメータロード成功")

        return target_freqs, tolerance_lower, tolerance_upper, cal

    def _get_target_parms_freq(self, stationid, day, day_wav_file_list, freq):
        # 分析日の全WAVファイルの異常検知パラメータ算出
        params = []
        for file in day_wav_file_list:
            fs, data = self.sp.wav_load(file)
            sub_data = data[:,0]
            slm_data = data[:,1]
            oct_mask = self.sp.make_oct_mask(freq, fs)
            try:
                slm_peak_lv = self.sp.cal_CPB_percentile_level(slm_data, oct_mask, fs, self.settings.sensitivity_peak_level_percentile)
                sub_peak_lv = self.sp.cal_CPB_percentile_level(sub_data, oct_mask, fs, self.settings.sensitivity_peak_level_percentile)
            except Exception as e:
                self.logger.app.error(f"{file}:オクターブバンドレベル算出に失敗したためデータ棄却-{e}")
                continue
            params.append(slm_peak_lv-sub_peak_lv)
        reload_limit_num = floor(len(day_wav_file_list)* self.settings.sensitivity_reload_limit_size)
        params, reload_count = self._delete_outlier_value(stationid, freq, params, reload_limit_num)
        if len(params) < self.settings.sensitivity_sample_size:
            start_day = day - timedelta(days= 1)
            start_time = datetime.combine(start_day, time(23,59,59))
            try:
                self._replenishment_param(stationid, start_time, freq, reload_limit_num-reload_count, params)
            except Exception as e:
                msg = f"対象日以前からの異常検知パラメータ補充処理に失敗-{e}"
                self.logger.app.error(msg)
                raise Exception(msg)
        return params

    def _replenishment_param(self, stationid, start_time, freq, reload_limit_num, params):
        # データ探索開始日時初期化
        time = start_time
        # 外れデータ棄却カウント数初期化
        reload_count = 0
        # パラメータが指定数になるまでループ処理
        while len(params) < self.settings.sensitivity_sample_size:
            try:
                event_time, file = self._get_target_event_time(stationid, time, direction = "backward")
            except Exception as e:
                msg = f"waveファイル探索処理に失敗、データを必要数集められませんでした[必要数:{self.settings.sensitivity_sample_size},不足数{self.settings.sensitivity_sample_size-len(params)}]"
                self.logger.app.error(msg)
                raise Exception(e)
            fs, data = self.sp.wav_load(file)
            sub_data = data[:,0]
            slm_data = data[:,1]
            oct_mask = self.sp.make_oct_mask(freq, fs)
            try:
                slm_peak_lv = self.sp.cal_CPB_percentile_level(slm_data, oct_mask, fs, self.settings.sensitivity_peak_level_percentile)
                sub_peak_lv = self.sp.cal_CPB_percentile_level(sub_data, oct_mask, fs, self.settings.sensitivity_peak_level_percentile)
            except Exception as e:
                self.logger.app.error(f"{file}:オクターブバンドレベル算出に失敗したためデータ棄却-{e}")
                continue
            params.append(slm_peak_lv-sub_peak_lv)
            time = event_time - timedelta(seconds = 1)
            reload_count += 1
            if reload_count > reload_limit_num:
                msg = f"データ読み込み数上限に達しました"
                raise Exception(msg)
        params, count = self._delete_outlier_value(stationid, freq, params, reload_limit_num)
        reload_count += count
        if reload_count > reload_limit_num:
            msg = f"異常検知パラメータ標準偏差が正常範囲内に収まりませんでした"
            raise Exception(msg)
        if len(params) >= self.settings.sensitivity_sample_size:
            msg = f"実音データ補充成功"
            self.logger.app.info(f"{msg}")
            return params

        return self._replenishment_param(stationid, time, freq, reload_limit_num, params)

    def _delete_outlier_value(self, stationid, freq, params, reload_limit_num):
        reload_count = 0
        try:
            std_normal = self.normal_parameters[stationid]["peak_stdv"][str(freq)]
        except Exception as e:
            msg = f"正常パラメータ[peak_stdv]の読込失敗"
            raise Exception(msg)
        while reload_count <= reload_limit_num:
            try:
                std = np.std(params, ddof = 1)
            except Exception as e:
                msg = f"標準偏差の算出に失敗-{e}"
                raise Exception(msg)
            if np.isnan(std):
                msg = f"異常検知パラメータ標準偏差が無効な値'nan'になりました"
                self.logger.app.warning(msg)
                raise Exception(msg)
            if std < std_normal:
                return params, reload_count
            else:
                dist = list(np.abs(params - np.mean(params)))
                idx = dist.index(max(dist))
                params.pop(idx)
                reload_count += 1
        msg = f"対象日内の異常検知パラメータが正常パラメータの標準偏差内に収まりませんでした"
        self.logger.app.error(msg)
        raise  Exception(msg)

    def _jadge_sensivity(self, cal, stid, freq, params, tolerance_lower, tolerance_upper, day):
        mean = np.mean(params)
        m_lower, m_upper = self._cal_mean_interval(params, self.settings.sensitivity_confidence_level)
        try:
            n_lower = self.normal_parameters[stid]["peak_interval_lower"][str(freq)]
            n_upper = self.normal_parameters[stid]["peak_interval_upper"][str(freq)]
        except Exception:
            msg = f"正常パラメータpeak_interval_lowerもしくはpeak_interval_upperの読込失敗"
            raise Exception(msg)
        if self.settings.valid_sensitivity_save_chart:
            sc.draw_sensitivity_histogram(cal, stid, freq, params, mean, m_lower, m_upper, n_lower, n_upper, tolerance_lower, tolerance_upper, self.settings.chart_save_directory, day)
            self.logger.app.debug(f"感度チェック分析分析画像出力成功")
        if n_lower + tolerance_lower > mean:
            self.logger.app.info(f"異常-{freq}Hz-マイク感度低い")
            return True
        elif n_upper + tolerance_upper < mean:
            self.logger.app.info(f"異常-{freq}Hz-マイク感度高い")
            return True
        else:
            self.logger.app.debug(f"異常なし-{freq}")
            return False