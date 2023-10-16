import json
from pathlib import Path

class Settings():
    """
    wave_dir            : waveファイルの保存ﾃﾞｨﾚｸﾄﾘ
    log_save_dir        : ログファイル保存先
    chart_save_dir      : 結果分析用png画像グラフの保存先

    fft_parameters
        fft_n               : fft点数 2のべき乗の値のみ int
        overlap_percent     : 1～100 float
        window              : 使用窓関数名 "hanning", "hamming", "blackman"
        wave_samplelate     : waveファイルのサンプリングレート これ以外を読み込もうとするとエラーになる int

    valid_common
        recurse_days                    : 異常検知を遡って実行する日数 int
        normaly_sample_size             : 正常データ,データの平均を求める際に使用するデータ数 int
        sample_valid_proportion_of_day  : sensitivity機能で実行対処日以前のデータを持ってこれるデータ数の割合の許容値 float 0～99
        use_common_calibrated_time      : 全測定局共通の校正完了時間を使うか true,false
        common_calibrated_time          : 全測定局共通の校正完了時間 "yyyy-mm-dd hh:mm:ss"
        target_frequency                : 全測定局共通の対象オクターブバンド周波数 [int,int...]
        propotion                       : 平均信頼区間推定時のp値 通常は0.95,0.99を使う float
        anormaly_tolerance              : anormary機能で異常判定の設定許容値
        sensitivity_tolerance           : sensitivity機能で異常判定の設定許容値

    station
        id                              : 測定局ID str
        name                            : 測定局名称 str
        execution                       : 異常検知実行するか true false
        calibrated_time                 : use_common_calibrated_timeがtrueであれば使われない校正完了時間 "yyyy-mm-dd hh:mm:ss"
        *target_frequency               : オプション 測定局ごとに記入があればこちらを使う 対象オクターブバンド周波数 [int,int...]
        """

    def __init__(self, settings_path: Path):

        # 設定ファイル読込
        with settings_path.open(mode='r', encoding='utf-8') as f:
            settings = json.load(f)
        self.settings_path = settings_path

        self.wave_dir = Path(settings['wave_dir'])
        self.log_save_dir = Path(settings['log_save_dir'])
        self.chart_save_dir = Path(settings['chart_save_dir'])

        self.fft_parameters = dict(settings['fft_parameters'])
        self.common = dict(settings['valid_common'])
        self.station = list(settings['station'])

    @classmethod
    def check_settings_format(cls, settings):
        pass