from datetime import datetime, timedelta, time, timedelta
import os
import glob
from signals import SignalProcesses
import numpy as np
from scipy import stats
from math import floor

class Detecter(object):

    def __init__(self, settings, logger):

        # 信号処理プロセス,アプリケーションログのインスタンス化
        self.logger = logger
        self.sp = SignalProcesses(settings, logger)

        # 全機能共通設定
        self.wave_dir = settings.wave_dir
        self.normaly_sample_size = settings.common["normaly_sample_size"]
        self.co_target_frequency  = list(settings.common['target_frequency'])
        self.recurse_days = settings.common["recurse_days"]
        self.day_list = self._get_target_days()

        #! stidに重複もしくは不正がないかチェックする処理を作る
        self.station_settings = settings.station

        #! 実行対象の測定局が存在しない場合に終了させる処理を作る
        self.target_station_list = self.get_target_station_list(self.station_settings)
        if not self.target_station_list:
            msg = "実行対象の測定局がないので終了します(設定ファイルのexecution:trueなし)"
            self.logger.app.info(msg)
            exit()

        self.logger.app.debug("Detecter class instantized")

    def get_target_station_list(self, station_settings):

        """
        設定ファイルの情報から異常検知実行対象になっている測定局IDのリストを作る
        """

        target_station_list = []
        for station in station_settings:
            if station["execution"] == True:
                target_station_list.append(station["id"])

        if target_station_list == []:
            return False

        return target_station_list

    def get_target_event_time(self, stid, st_time, next = False, direction = "advance"):


        """
        st_timeから未来もしくは過去へ遡り(引数directionで指定)、最も近い騒音イベント時刻を取得する
        探索対象は実音ファイル名(Dファイルは使わない)
        """

        if next == True and direction == "advance":
            st_time = (st_time + timedelta(days = 1)).replace(hour = 0, minute = 0, second = 0)
        elif next == True and direction == "backward":
            st_time = (st_time - timedelta(days = 1)).replace(hour = 23, minute = 59, second = 59)

        if st_time.date() >= datetime.now().date() and next == False:
            #! Critical
            msg = "st_timeは今日より前の日付を指定して下さい:{}".format(st_time)
            self.logger.app.critical(msg)
            raise Exception(msg)

        elif st_time.date() >= datetime.now().date() and next == True and direction == "advance":
            #! Warning
            msg = "{}-今日より先の日付は探せない-{}".format(stid,st_time.date())
            self.logger.app.info(msg)
            return False, msg

        #! システムの稼働開始日を設定ファイルに書いておいてその日以前のデータは探しに行かないようにする
        elif st_time.date() < datetime(2022,12,1).date() and next == True and direction == "backward":
            msg = "{}-これ以上前の日付は探せない:{}".format(stid, datetime(2022,12,1).date())
            self.logger.app.info(msg)
            return False, msg

        target_dir = os.path.join(self.wave_dir, st_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'))

        if os.path.isdir(target_dir) == False:
            self.logger.app.warning("失敗:対象日のディレクトリが存在しません:",target_dir)
            return self.get_target_event_time(stid, st_time, next = True, direction = direction)

        wav_list = glob.glob(os.path.join(target_dir,'**','*.WAV'), recursive = True)

        if wav_list == []:
            self.logger.app.warning("失敗:対象ディレクトリ内にWAVEファイルが存在しません:",target_dir)
            return self.get_target_event_time(stid, st_time, next = True, direction = direction)

        day_event_time_list = []
        for file in wav_list:
            fname = os.path.splitext(os.path.basename(file))[0]
            day_event_time_list.append(datetime.strptime(fname, '%y%m%d%H%M%S'))
        wav_list.clear()

        if direction == "advance":
            day_event_time_list = sorted(day_event_time_list,reverse=False)
        elif direction == "backward":
            day_event_time_list = sorted(day_event_time_list,reverse=True)

        # waveファイル名から騒音イベント時刻を得て指定時間との差を求める
        for event_time in day_event_time_list:

            if direction == "advance":
                if event_time == st_time or event_time >= st_time:
                    path = os.path.join(self.wave_dir, event_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'),
                                        datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
                    # 成功
                    return event_time, path
            elif direction == "backward":
                if event_time == st_time or event_time <= st_time:
                    path = os.path.join(self.wave_dir, event_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'),
                                        datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
                    # 成功
                    return event_time, path

        return self.get_target_event_time(stid, st_time, next = True, direction = direction)

    def cal_mean_interval(self, data, proportion):


        """
        分布の母平均信頼区間を求める
        """

        # 形状パラメータ(自由度)を指定
        dof = len(data) -1
        # 位置パラメータを指定
        mean = np.mean(data)
        # 尺度パラメータを指定
        scale = np.std(data)

        t_data = stats.t(loc = mean, scale = scale, df = dof)
        bottom, up = t_data.interval(alpha = proportion)

        return bottom, up

    def _get_target_days(self):

        day_list = []
        for i in range(self.recurse_days):
            day_list.append(datetime.now().date() - timedelta(days = i + 1))

        return day_list

class Anormaly(Detecter):

    """
    故障診断機能クラス
    """

    def __init__(self, settings, logger, normal_parameters):

        super().__init__(settings, logger)
        self.normal_parameters = normal_parameters
        self.co_tolerance  = float(settings.common['anormaly_tolerance'])
        self.recurse_days = settings.common["recurse_days"]

        self.logger.app.debug("Anormaly")


    def _get_parm_freq(self, signal, oct_freq_mask):
        """
        """

        sub_ch = signal[:,0]
        slm_ch = signal[:,1]
        slm_lv = self.sp.cal_CPB_level2(slm_ch, oct_freq_mask)
        sub_lv = self.sp.cal_CPB_level2(sub_ch, oct_freq_mask)

        parm = slm_lv - sub_lv

        return parm


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


    def _judge_anormaly(self, stid, freq, data, tolerance):
        """
        異常検知の実行
        """

        if (self.normal_parameters[stid]["norm_interval_lower"][str(freq)] - tolerance) > data:
            return 1
        elif (self.normal_parameters[stid]["norm_interval_upper"][str(freq)]) + tolerance < data:
            return 2
        else:
            return False


    def _do_valid_station(self, stid):
        """
        測定局別処理 故障診断
        """

        msg_list = []

        # 測定局設定読込
        freqs, tolerance = self._load_station_settings(stid)

        # バンドパスフィルタ
        oct_freq_mask = {}
        for freq in freqs:
            oct_freq_mask[str(freq)] = self.sp.make_oct_mask(freq)

        # 日別処理
        for day in self.day_list:

            wave_file_list = []
            target_dir = os.path.join(self.wave_dir, day.strftime('%Y%m'), stid, day.strftime('%Y%m%d'))

            if os.path.isdir(target_dir) == True:
                wave_file_list += glob.glob(os.path.join(target_dir,'**','*.WAV'),recursive = True)
            else:
                #! Warning
                msg = "ディレクトリが存在しません,故障診断できませんでした:{}:{}", format(stid, target_dir)
                self.logger.app.warning(msg)
                return False

            if wave_file_list == []:
                #! Warning
                msg  = "対象期間内にWAVEファイルが存在しません,故障診断できませんでした:{}:{}", format(stid, day)
                self.logger.app.warning(msg)
                return False

            # ファイルごとの処理
            for file in wave_file_list:
                signal = self.sp.wav_load(file)
                anorm_freqs = []
                for freq in freqs:
                    param = self._get_parm_freq(signal, oct_freq_mask[str(freq)])
                    if param != False:
                        jadge = self._judge_anormaly(stid, freq, param, tolerance)
                        if jadge != False:
                            anorm_freqs.append(freq)
                    else:
                        break
                if anorm_freqs != []:
                    # msg_list.append("anormly-{}-[{}]-{}"
                    #                 .format(stid, ",".join(map(str, anorm_freqs)), os.path.basename(file)))
                    msg = "anormly-{}-[{}]-{}".format(stid, ",".join(map(str, anorm_freqs)), os.path.basename(file))
                    self.logger.result.info(msg)

            self.logger.app.debug("anormary-{}-complete".format(day))

        return msg_list


    def do_valid_anormaly(self):

        msg_list = []
        for stid in self.target_station_list:
            station_msg = self._do_valid_station(stid)
            if station_msg != []:
                msg_list.append(station_msg)
            self.logger.app.debug("anormary-{}-complete".format(stid))

        return msg_list

class Sensitiviy(Detecter):

    """
    騒音計マイク感度異常診断機能クラス
    """

    def __init__(self, settings, logger, normal_parameters):

        super().__init__(settings, logger)
        self.normal_parameters = normal_parameters
        self.co_tolerance  = float(settings.common["sensitivity_tolerance"])
        self.sample_reload_limit_percent_of_day = float(settings.common["sample_reload_limit_percent_of_day"])
        self.sample_reload_limit_number = floor(self.normaly_sample_size * self.sample_reload_limit_percent_of_day /100.0)

        self.logger.app.debug("Sensitiviy")


    def do_valid_sensitivity(self):

        msg_list = []
        for stid in self.target_station_list:
            station_msg = self._do_valid_station(stid)
            if station_msg != []:
                msg_list.append(station_msg)
            self.logger.app.debug("sensitiviy-{}-complete".format(stid))

        return msg_list


    def _do_valid_station(self, stid):
        """
        測定局別処理 感度異常診断
        """

        msg_list = []

        # 測定局設定読込
        freqs, tolerance = self._load_station_settings(stid)

        # バンドパスフィルタ
        self.oct_freq_mask = {}
        for freq in freqs:
            self.oct_freq_mask[str(freq)] = self.sp.make_oct_mask(freq)

        # 日別処理
        for day in self.day_list:

            st_time = datetime.combine(day, time(23,59,59))

            # 周波数ごとの処理
            anorm_freqs = []
            for freq in freqs:
                params = self._get_target_parms(stid, st_time, freq)
                if params == False:
                    #! ログ書く
                    self.logger.app.info("{}-{}-感度異常診断を実行できませんでした".format(stid, day))
                    break
                elif params == -1:
                    self.logger.app.info("{}-{}-{}-分散が正常値に収まらなかったため、感度異常診断ができませんでした".format(stid, day, freq))
                    jadge = False
                else:
                    jadge = self._jadge_sensivity(stid, freq, params, tolerance)

                if jadge != False:
                    anorm_freqs.append(freq)

            if anorm_freqs != []:
                msg = "sensitivity-{}-[{}]-{}".format(stid, ",".join(map(str, anorm_freqs)), day)
                msg_list.append(msg)
                self.logger.result.info(msg)

            self.logger.app.debug("sensitiviy-{}-complete".format(day))

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

        time = st_time

        if params == None:
            params = []

        reload_count = 0
        # パラメータが指定数になるまでループ処理
        while len(params) < self.normaly_sample_size:
            event_time, path = self.get_target_event_time(stid, time, direction = "backward")

            if event_time == False:
                self.logger.app.info("データを必要数集められませんでした[必要数:{},不足数{}]".format(self.normaly_sample_size,self.normaly_sample_size - len(params)))
                return False

            signal = self.sp.wav_load(path)
            sub_data = signal[:,0]
            slm_data = signal[:,1]

            slm_lv = self.sp.cal_CPB_level2(slm_data, self.oct_freq_mask[str(freq)])
            sub_lv = self.sp.cal_CPB_level2(sub_data, self.oct_freq_mask[str(freq)])
            params.append(slm_lv - sub_lv)

            time = event_time - timedelta(seconds = 1)

        params, count = self._delete_outlier_value(stid, freq, params)
        reload_count += count

        if reload_count > self.sample_reload_limit_number:
            return -1

        if len(params) == self.normaly_sample_size:
            return params

        return self._get_target_parms(stid, time, freq, params)


    def _delete_outlier_value(self, stid, freq, params):
        count = 0
        while count <= self.sample_reload_limit_number:
            var = np.var(params, ddof=1)
            if var > self.normal_parameters[stid]["norm_var"][str(freq)]:
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

        if self.normal_parameters[stid]["norm_interval_lower"][str(freq)] - tolerance > np.mean(params):
            return 1
        elif self.normal_parameters[stid]["norm_interval_upper"][str(freq)] + tolerance < np.mean(params):
            return 2

        return False