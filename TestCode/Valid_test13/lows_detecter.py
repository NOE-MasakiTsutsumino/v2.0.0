from detecter import Detecter
from signals import SignalProcesses
from os import path
from glob import glob

class Lows_Detecter(Detecter):

    """
    騒音計マイク故障検知クラス
    """

    def __init__(self, settings, logger):

        # 親クラス継承
        super().__init__(settings, logger)
        self.sp = SignalProcesses(settings, logger)

        self.floor_level_percentile = settings.floor_level_percentile

        self.logger.app_logger.info("Lows_Detecter class instantized")

    def do_valid(self):

            # 検知メッセージ初期化
            msg_list = []

            # 測定局毎にループ
            for stid in self.target_station_list:
                # 異常検知実行
                station_msg = self._do_valid_station(stid)
                # 異常メッセージがあれば出力に追加
                if station_msg != []:
                    msg_list += station_msg

                self.logger.app_logger.info(f"lows - {stid} - complete")

            return msg_list

    def _do_valid_station(self, stid):
        """
        測定局別処理 異常検知
        """

        # 正常パラメータが算出済みか調べる
        if not self.check_calculated_norm(stid, self.normal_params):
            msg = f"正常パラメータが未算出です:{stid}"
            self.logger.app.error(msg)
            return False

        # 出力初期化
        msg_list = []

        # 測定局設定読込
        freqs, tolerance = self._load_station_settings(stid)

        # 日別処理
        for day in self.target_day_list:

            # 実音データの格納ディレクトリ
            wave_file_list = []
            target_dir = path.join(self.wav_directory, day.strftime('%Y%m'), stid, day.strftime('%Y%m%d'))

            if path.isdir(target_dir):
                wave_file_list += glob(path.join(target_dir,'**','*.WAV'),recursive = True)
            else:
                msg = f"ディレクトリが存在しません,故障診断できませんでした:{stid}:{target_dir}"
                self.logger.app_logger.error(msg)
                continue

            if wave_file_list == []:
                msg  = f"対象期間内にWAVEファイルが存在しません。{stid}:{day}"
                self.logger.app_logger.error(msg)
                continue

            msg = f"{stid}-{day}-異常検知実行実音ファイル数-{len(wave_file_list)}"
            self.logger.app_logger.info(msg)

            # 実音ファイル別処理
            for file in wave_file_list:
                # 実音ファイル読み込み
                fs, data = self.sp.wav_load(file)
                # 異常検知メッセージ初期化
                anorm_freqs = []
                # オクターブバンド別処理
                for freq in freqs:
                    # 異常検知パラメータ算出
                    param_list = self._get_parm_freq(data, fs, freq)
                    self.logger.app_logger.debug(f"パラメータ:{freq}:{param_list}")
                    if param_list:
                        # 異常判定
                        jadge, msg = self._judge_lows(stid, freq, param_list, tolerance)
                        # 異常があればオクターブバンド周波数を記録
                        if jadge:
                            anorm_freqs.append(freq)
                    else:
                        # 異常がなければ終了
                        break
                # 異常があった場合、メッセージをロギング
                if anorm_freqs != []:
                    # メッセージの整理
                    msg = "lows_detecter-{}-[{}]-{}".format(stid, ",".join(map(str, anorm_freqs)), path.basename(file))
                    self.logger.result.warning(f"lows,{stid},{day},{file},{anorm_freqs},異常あり")
                    msg_list.append(msg)
                else:
                    self.logger.result.info(f"lows,{stid},{file},異常なし")

            self.logger.app_logger.info(f"lows_detecter - {stid} - {day} - complete")

        return msg_list

    def _get_parm_freq(self, signal, fs, freq):
        """
        実音ファイルから異常検知パラメータ算出
        peakと暗騒音を返す
        """

        param_list = {}
        sub_data = signal[:,0]
        slm_data = signal[:,1]

        oct_mask = self.sp.make_oct_mask(freq, fs)

        slm_floor_lv = self.sp.cal_CPB_percentile_level(slm_data, oct_mask, fs, self.floor_level_percentile)
        if not slm_floor_lv:
            self.logger.app_logger.error(f"オクターブバンドレベル算出に失敗")
            return False

        sub_floor_lv = self.sp.cal_CPB_percentile_level(sub_data, oct_mask, fs, self.floor_level_percentile)
        param_list["floor"] = slm_floor_lv - sub_floor_lv

        return param_list

    def _load_station_settings(self, stid):

        freqs  = self.station_settings["id" == stid]["lows_target_freqency"]
        t = self.station_settings["id" == stid]["lows_tolerance"]

        return freqs, t

    def _judge_lows(self, stid, freq, param_list: dict, tolerance):
        """
        異常検知パラメータを閾値で判定
        """

        if (self.normal_params[stid]["floor_interval_lower"][str(freq)] - tolerance) > param_list["floor"]:
            msg = f"異常あり - {freq} - floor_lower"
            self.logger.app_logger.debug(msg)
            return True, msg
        elif (self.normal_params[stid]["floor_interval_upper"][str(freq)]) + tolerance < param_list["floor"]:
            msg = f"異常あり - {freq} - floor_upper"
            self.logger.app_logger.debug(msg)
            return True, msg
        else:
            self.logger.app_logger.debug(f"異常なし - {freq}")
            msg = ""
            return False, msg
