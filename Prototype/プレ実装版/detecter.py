""" encoding utf-8

異常検知共通機能クラス
"""

# imports1
from datetime import datetime, timedelta ,timedelta
import os
import glob
import numpy as np
from scipy import stats
import json

# code
class Detecter(object):
    def __init__(self, settings, logger):
        self.__logger = logger
        self.__settings = settings
        self.__target_day_list = self._get_target_days(self.settings.return_days)
        self.__logger.app.debug("instantized")

    def _get_target_days(self, return_days):
        target_day_list = []
        for i in range(return_days):
            target_day = datetime.now().date() - timedelta(days = i + 1)
            if target_day >= self.settings.system_start_date.date():
                target_day_list.append(datetime.now().date() - timedelta(days = i + 1))
        return target_day_list

    def _get_target_station_list(self, settings, keyword):
        target_station_list = []
        for station in settings.station_settings:
            if station[keyword] == True:
                target_station_list.append(station["stationid"])
        if target_station_list == []:
            return False

        return target_station_list

    def _get_target_event_time(self, stid, st_time, next = False, direction = "advance"):
        if next == True and direction == "advance":
            st_time = (st_time + timedelta(days = 1)).replace(hour=0, minute=0, second=0)
        elif next == True and direction == "backward":
            st_time = (st_time - timedelta(days = 1)).replace(hour=23, minute=59, second=59)
        if st_time.date() >= datetime.now().date() and not next:
            msg = f"st_timeを現在日以降に指定する事はできません[{st_time}]"
            self.logger.app.critical(msg)
            raise Exception(msg)
        elif st_time.date() >= datetime.now().date() and next and direction == "advance":
            msg = f"現在日以降の日付は探索できません"
            self.logger.app.debug(msg)
            return False, msg
        elif st_time.date() < self.settings.system_start_date.date() and next and direction == "backward":
            msg = f"system_start_date以前の時刻は探索できません"
            self.logger.app.debug(msg)
            return False, msg
        target_dir = os.path.join(self.settings.wav_directory, st_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'))
        if os.path.isdir(target_dir) == False:
            self.logger.app.debug(f"ディレクトリが存在しません[{target_dir}]")
            return self._get_target_event_time(stid, st_time, next=True, direction = direction)
        wav_list = glob.glob(os.path.join(target_dir,'**','*.WAV'), recursive = True)
        if wav_list == []:
            self.logger.app.debug(f"ディレクトリ内にWAVEファイルが存在しません[{target_dir}]")
            return self._get_target_event_time(stid, st_time, next=True, direction = direction)
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
                    path = os.path.join(self.settings.wav_directory, event_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'),
                                        datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
                    # 成功
                    return event_time, path
            elif direction == "backward":
                if event_time == st_time or event_time <= st_time:
                    path = os.path.join(self.settings.wav_directory, event_time.strftime('%Y%m'), stid, st_time.strftime('%Y%m%d'),
                                        datetime.strftime(event_time, '%y%m%d%H%M%S') + ".WAV")
                    # 成功
                    return event_time, path

        return self._get_target_event_time(stid, st_time, next=True, direction=direction)

    def _cal_mean_interval(self, data, confidence):
        n = len(data)
        dof = n-1
        mean = np.mean(data)
        scale = np.std(data,ddof=1)/np.sqrt(n)
        t_data = stats.t(loc=mean, scale=scale, df=dof)
        lower, upper = t_data.interval(alpha = confidence)
        return lower, upper

    def _load_normal_parameters_file(self):
        filename = "NORMAL_PARAMETERS.json"
        try:
            with open(filename) as f:
                data = json.load(f)
                self.logger.app.debug(f"正常パラメータファイルロード成功")
        except Exception as e:
                msg = f"正常パラメータファイル:NORMAL_PARAMETERS.jsonがありません[{e}]"
                self.logger.app.critical(msg)
                raise Exception(msg)
        return data

    @property
    def logger(self):
        return self.__logger
    @property
    def settings(self):
        return self.__settings
    @property
    def  target_day_list(self):
        return self.__target_day_list