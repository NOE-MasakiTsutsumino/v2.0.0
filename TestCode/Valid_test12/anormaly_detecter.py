from detecter import Detecter
import os
import glob

class Anormaly_Detecter(Detecter):

    """
    騒音計マイク故障検知クラス
    """

    def __init__(self, settings, logger):

        # 親クラス継承
        super().__init__(settings, logger)

        # 閾値取得
        self.co_tolerance  = float(settings.common['anormaly_tolerance'])
        self.logger.app.debug(f"anormaly_tolerance:{self.co_tolerance}")

        # 何日前まで遡って実行するか
        self.recurse_days = settings.common["recurse_days"]
        self.logger.app.debug(f"recurse_days:{self.recurse_days}")

        self.logger.app.info("Anormaly_Detecter class instantized")

    def _get_parm_freq(self, signal, freq):
        """
        実音ファイルから異常検知パラメータ算出
        """

        param_list = {}

        sub_data = signal[:,0]
        slm_data = signal[:,1]

        # オクターブバンドレベルの平均差
        slm_mean_lv = self.sp.cal_CPB_mean_level(slm_data, self.sp.oct_freq_mask[str(freq)])

        # 演算失敗チェック
        if not slm_mean_lv:
            self.logger.app.error(f"オクターブバンドレベル算出に失敗")
            return False

        sub_mean_lv = self.sp.cal_CPB_mean_level(sub_data, self.sp.oct_freq_mask[str(freq)])
        param_list["mean"] = slm_mean_lv - sub_mean_lv

        # ピーク付近のレベル差
        slm_peak_lv = self.sp.cal_CPB_percentile_level(slm_data, self.sp.oct_freq_mask[str(freq)], 90)
        sub_peak_lv = self.sp.cal_CPB_percentile_level(sub_data, self.sp.oct_freq_mask[str(freq)], 90)
        param_list["peak"] = slm_peak_lv - sub_peak_lv

        # 暗騒音付近のレベル差
        slm_floor_lv = self.sp.cal_CPB_percentile_level(slm_data, self.sp.oct_freq_mask[str(freq)], 10)
        sub_floor_lv = self.sp.cal_CPB_percentile_level(sub_data, self.sp.oct_freq_mask[str(freq)], 10)
        param_list["floor"] = slm_floor_lv - sub_floor_lv

        return param_list

    def _load_station_settings(self, stid):

        if "target_frequency" in self.station_settings["id"==stid]:
            freqs  = self.station_settings["id" == stid]["target_frequency"]
        else:
            freqs = self.co_target_frequency

        if "anormaly_tolerance" in self.station_settings["id"==stid]:
            t = self.station_settings["id" == stid]["anormaly_tolerance"]
        else:
            t = self.co_tolerance

        return freqs, t

    def _judge_anormaly(self, stid, freq, param_list: dict, tolerance):
        """
        異常検知パラメータを閾値で判定
        """

        if (self.normal_params[stid]["peak_norm_interval_lower"][str(freq)] - tolerance) > param_list["peak"]:
            self.logger.app.debug(f"異常 - {freq} - peak_lower")
            return False
        elif (self.normal_params[stid]["peak_norm_interval_upper"][str(freq)]) + tolerance < param_list["peak"]:
            self.logger.app.debug(f"異常 - {freq} - peak_uppper")
            return False
        elif (self.normal_params[stid]["floor_norm_interval_lower"][str(freq)] - tolerance) > param_list["floor"]:
            self.logger.app.debug(f"異常 - {freq} - floor_lower")
            return False
        elif (self.normal_params[stid]["floor_norm_interval_upper"][str(freq)]) + tolerance < param_list["floor"]:
            self.logger.app.debug(f"異常 - {freq} - floor_upper")
            return False
        else:
            self.logger.app.debug(f"異常なし - {freq}")
            return True

    def _do_valid_station(self, stid):
        """
        測定局別処理 異常検知
        """

        # 正常パラメータが算出済みか調べる
        if not self._check_calculated_norm(stid, self.normal_params):
            msg = f"正常パラメータが未算出です:{stid}"
            self.logger.app.error(msg)
            return False

        # 測定局設定読込
        freqs, tolerance = self._load_station_settings(stid)

        # 日別処理
        for day in self.day_list:

            # 実音データの格納ディレクトリ
            wave_file_list = []
            target_dir = os.path.join(self.wave_dir, day.strftime('%Y%m'), stid, day.strftime('%Y%m%d'))

            if os.path.isdir(target_dir):
                wave_file_list += glob.glob(os.path.join(target_dir,'**','*.WAV'),recursive = True)
            else:
                msg = f"ディレクトリが存在しません,故障診断できませんでした:{stid}:{target_dir}"
                self.logger.app.error(msg)
                continue

            if wave_file_list == []:
                msg  = "対象期間内にWAVEファイルが存在しません。{}:{}", format(stid, day)
                self.logger.app.error(msg)
                continue

            # 実音ファイル別処理
            for file in wave_file_list:
                # 実音ファイル読み込み
                signal = self.sp.wav_load(file)
                # 異常検知メッセージ初期化
                anorm_freqs = []
                # オクターブバンド別処理
                for freq in freqs:
                    # 異常検知パラメータ算出
                    param_list = self._get_parm_freq(signal, freq)
                    self.logger.app.debug(f"パラメータ:{freq}:{param_list}")
                    if param_list:
                        # 異常判定
                        jadge = self._judge_anormaly(stid, freq, param_list, tolerance)
                        # 異常があればオクターブバンド周波数を記録
                        if not jadge:
                            anorm_freqs.append(freq)
                    else:
                        # 異常がなければ終了
                        break
                # 異常があった場合、メッセージをロギング
                if anorm_freqs != []:
                    # msg_list.append("anormly-{}-[{}]-{}"
                    #                 .format(stid, ",".join(map(str, anorm_freqs)), os.path.basename(file)))
                    # メッセージの整理
                    msg = "anormly_detecter-{}-[{}]-{}".format(stid, ",".join(map(str, anorm_freqs)), os.path.basename(file))
                    # ログ出力
                    self.logger.result.warning(msg)

            self.logger.app.info(f"anormary_detecter - {stid} - {day} - complete")

        return True

    def do_valid(self):

        # 検知メッセージ初期化
        msg_list = []

        # 測定局毎にループ
        for stid in self.target_station_list:
            # 異常検知実行
            station_msg = self._do_valid_station(stid)
            # 異常メッセージがあれば出力に追加
            if (station_msg != []) and (not station_msg):
                msg_list.append(station_msg)

            self.logger.app.info(f"anormary - {stid} - complete")

        return msg_list