from detecter import Detecter
from signals import SignalProcesses
from os import path
from glob import glob

class Anormaly_getecter(Detecter):
    """
    ノイズ混入，無音など実音データの一部で生じる異常の検知クラス
    """

    def __init__(self, settings, logger):

        # 親クラス継承
        super().__init__(settings, logger)
        self.sp = SignalProcesses(settings, logger)

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

            self.logger.app_logger.info(f"anormary - {stid} - complete")

    def _do_valid_station(self, stid):
        """
        測定局別処理 異常検知
        """

        # 出力初期化
        msg_list = []

        # 測定局設定読込
        detection_width, tolerance = self._load_station_settings(stid)

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
                _, data = self.sp.wav_load(file)

                # 異常検知メッセージ初期化
                param_list = self._get_parms_wav(data, detection_width)
                if param_list:
                    # 異常判定
                    jadge, msg = self._judge_anormaly(stid, param_list, tolerance)

                # 異常があった場合、メッセージをロギング
                if jadge:
                    # メッセージの整理
                    self.logger.result.warning(f"anormaly,{stid},{day},{file},異常あり")
                    msg_list.append(msg)
                else:
                    self.logger.result.info(f"anormaly,{stid},{file},異常なし")

            self.logger.app_logger.info(f"anormaly_detecter - {stid} - {day} - complete")

        return msg_list

    def _load_station_settings(self, stid):

        detection_width = int(self.station_settings["id" == stid]["anormaly_detection_width"])
        tolerance = float(self.station_settings["id" == stid]["anormaly_tolerance"])

        return detection_width, tolerance

    def _get_parms_wav(self, signal, detection_width):
        """
        実音ファイルから異常検知パラメータ算出
        """

        param_list = []
        sub_data = signal[:,0]
        slm_data = signal[:,1]

        slm_lv = self.sp.cal_mean_level(slm_data, detection_width)
        if not slm_lv:
            self.logger.app_logger.error(f"オクターブバンドレベル算出に失敗")
            return False

        sub_lv = self.sp.cal_mean_level(sub_data, detection_width)
        param_list.append(slm_lv - sub_lv)

        return param_list

    def _judge_anormaly(self, stid, param_list, tolerance):
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