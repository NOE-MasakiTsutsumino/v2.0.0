import glob
from datetime import datetime
import os

WAVE_DIR = "D:\\Diana\\新千歳空港\\WAVE"
TARGET_DAY = datetime(2023,10,30).date()
STID = "CH53"

def main():

    wave_file_list = []
    target_dir = os.path.join(WAVE_DIR, TARGET_DAY.strftime('%Y%m'), STID, TARGET_DAY.strftime('%Y%m%d'))

    if os.path.isdir(target_dir):
        wave_file_list += glob.glob(os.path.join(target_dir,'**','*.WAV'),recursive = True)
    else:
        msg = f"ディレクトリが存在しません:{target_dir}"
        raise Exception(msg)

    if wave_file_list == []:
        msg  = f"対象期間内にWAVEファイルが存在しません。{STID}:{TARGET_DAY}"
        raise Exception(msg)

if __name__ == "__main__":

    try:
        main()
    except:
        print("失敗しちゃった")