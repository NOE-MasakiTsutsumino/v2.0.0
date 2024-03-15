# encoding utf-8

# imports
from detecter import Detecter
from signals import SignalProcesses
from glob import glob
import os
from save_chart import DrawCharts as dc

# code
class FailureDetecter(Detecter):

    def __init__(self, settings, logger):
        super().__init__(settings, logger)
        self.sp = SignalProcesses(settings, logger)
        self.logger.app.debug("instantized")

    def do_valid(self):
        # 異常メッセージ初期化
        anormaly_msg_list = []
        # 実行対象測定局リスト作成
        target_station_list = self._get_target_station_list(self.settings,"failure_valid")
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
            # 異常メッセージがあればリストに追加
            if station_msg != []:
                anormaly_msg_list += station_msg

        return anormaly_msg_list

    def _do_valid_station(self, stationid):
        # 出力初期化
        msg_list = []
        draw_data = {}
        # 測定局設定読込
        target_freqs, tolerance = self.__load_station_settings(stationid)
        for freq in target_freqs:
            draw_data[str(freq)] = []

        # 日別処理
        for day in self.target_day_list:
            # 実音データの格納ディレクトリパス作成
            target_dir = os.path.join(self.settings.wav_directory, day.strftime('%Y%m'), stationid, day.strftime('%Y%m%d'))

            try:
                day_wav_file_list = glob(os.path.join(target_dir,'*.WAV'))
                if len(day_wav_file_list) < 1:
                    msg = f"{stationid}-{day}:対象日付フォルダ内にWAVファイルがありません、分析失敗"
                    self.logger.app.error(msg)
                    continue
            except Exception as e:
                msg = f"{stationid}-{day}:WAVファイルリストの取得に失敗しました[{e}]"
                self.logger.app.error(msg)
                continue

            # 実音ファイル別処理
            for file in day_wav_file_list:
                # 実音ファイル読み込み
                fs, data = self.sp.wav_load(file)
                # 異常検知メッセージ初期化
                anormaly_freqs = []
                # オクターブバンド別処理
                for freq in target_freqs:

                    # 異常検知パラメータ算出
                    sub_data = data[:,0]
                    slm_data = data[:,1]
                    oct_mask = self.sp.make_oct_mask(freq, fs)

                    try:
                        slm_floor_lv = self.sp.cal_CPB_percentile_level(slm_data, oct_mask, fs, self.settings.failure_floor_level_percentile)
                        sub_floor_lv = self.sp.cal_CPB_percentile_level(sub_data, oct_mask, fs, self.settings.failure_floor_level_percentile)
                    except BaseException as e:
                        msg = f"{os.path.basename(file)}-オクターブバンドレベル算出に失敗したため実音ファイル棄却-{e}"
                        self.logger.app.error(msg)
                        continue
                    parameter = slm_floor_lv-sub_floor_lv
                    draw_data[str(freq)].append(parameter)
                    try:
                        jadge, msg = self.__judge_failure(stationid, parameter, freq, tolerance)
                    except BaseException as e:
                        self.logger.app.error(f"{freq}Hz-異常判定失敗-{e}")
                        continue
                    if jadge:
                        anormaly_freqs.append(freq)
                        self.logger.result.warning(f"{stationid}-{os.path.basename(file)}-{str(freq)}Hz-{msg}")
                if anormaly_freqs != []:
                    msg = "{}:騒音計故障チェック閾値超過[{}]-{}".format(stationid, ",".join(map(str, anormaly_freqs)), os.path.basename(file))
                    msg_list.append(msg)

            dc.draw_failure_histogram(stationid, day, target_freqs, draw_data, tolerance, self.normal_parameters, self.settings.chart_save_directory)
            for freq in target_freqs:
                draw_data[str(freq)] = []

            if msg_list == []:
                self.logger.result.info(f"{stationid}-{day}-マイク故障チェック異常なし")
                self.logger.app.info(f"{stationid}-{day}-マイク故障チェック異常なし")

        return msg_list

    def __load_station_settings(self, stationid):
        target_freqs  = self.settings.station_settings["stationid" == stationid]["failure_target_freqency"]
        tolerance = self.settings.station_settings["stationid"==stationid]["failure_tolerance"]

        return target_freqs, tolerance

    def __judge_failure(self, stationid, parameter, freq, tolerance):

        interval_low = self.normal_parameters[stationid]["floor_interval_upper"][str(freq)]
        interval_up = self.normal_parameters[stationid]["floor_interval_lower"][str(freq)]

        if parameter > interval_low + tolerance:
            msg = f"異常-故障チェック正常範囲超過"
            return True, msg
        elif parameter < interval_up - tolerance:
            msg = f"異常-故障チェック正常範囲未満"
            return True, msg
        else:
            msg = None
            return False, msg