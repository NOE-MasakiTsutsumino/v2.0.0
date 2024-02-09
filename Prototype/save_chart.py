from matplotlib import pyplot as plt
import os


class DrawCharts():

    @classmethod
    def draw_sensitivity_histogram(cls, cal, stid, freq, params, mean, m_lower, m_upper, n_lower, n_upper, tolerance_lower, tolerance_upper, dir, day):

        fig_dir = os.path.join(dir,day.strftime('%Y%m%d'))
        if not os.path.exists(fig_dir):
            os.makedirs(fig_dir)

        fig = plt.figure()
        ax = fig.add_subplot()

        plt.axvline(mean, color='orange', linestyle='dashed', linewidth=1)
        # plt.axvspan(m_lower, m_upper, color="orange",alpha = 0.3)
        plt.hist(params,alpha = 0.5, bins = 10)
        plt.axvspan(n_lower, n_upper, color="skyblue",alpha = 0.3)

        plt.axvspan(n_lower + tolerance_lower, n_lower, color="lightgreen",alpha = 0.3)
        plt.axvspan(n_upper, n_upper + tolerance_upper, color="lightgreen",alpha = 0.3)
        plt.legend([f"SLM-SubMic diff mean = {str(f'{mean:.2g}')}", f"normal_interval = {n_lower:.2g} to {n_upper:.2g}", f"tolerance = {tolerance_lower + n_lower:.2g} to {tolerance_upper + n_upper:.2g}"], loc='upper left')
        plt.text(0.5,-0.1, f"[Internal_cal ={cal}]",horizontalalignment="center",transform=ax.transAxes)
        plt.xlim([-1.5,1.5])
        plt.grid()
        plt.title(f"{stid} - {str(freq)}Hz")
        plt.tight_layout()

        fig.savefig(os.path.join(fig_dir,"sensitivity_" + day.strftime('%Y%m%d') + "_" + str(freq) + "Hz.png"))
        plt.close()

        return fig

    @classmethod
    def draw_learning_parameters_histogram(cls, parameters,stationid,freq,title):
        fig = plt.figure()
        plt.hist(parameters,alpha = 0.5, bins = 10)
        plt.grid()
        plt.title(f"learning_parameters_chart-{title}-[{stationid} - {freq}Hz]")
        plt.tight_layout()

        return fig

    @classmethod
    def draw_failure_histogram(cls, stationid, day, target_freqs, draw_data, tolerance, normal_parameters, dir):
        fig_dir = os.path.join(dir,day.strftime('%Y%m%d'))
        if not os.path.exists(fig_dir):
            os.makedirs(fig_dir)
        import csv
        
        
        
        # ax = fig.add_subplot()
        for freq in target_freqs:
            fig = plt.figure()
            interval_low = normal_parameters[stationid]["floor_interval_upper"][str(freq)]
            interval_up = normal_parameters[stationid]["floor_interval_lower"][str(freq)]

            plt.hist(draw_data[str(freq)],alpha = 0.5, bins = 10)
            plt.axvspan(interval_low,interval_up, color="skyblue",alpha = 0.3)
            plt.axvspan(interval_low - tolerance, interval_low, color="lightgreen",alpha = 0.3)
            plt.axvspan(interval_up, interval_up + tolerance, color="lightgreen",alpha = 0.3)
            plt.legend([f"normal_interval = {interval_low:.2g} to {interval_up:.2g}", f"tolerance = {interval_low - tolerance:.2g} to {interval_up + tolerance:.2g}"], loc='upper left')
            plt.grid()
            plt.title(f"failure_histogram-{stationid} - {freq}Hz")
            plt.tight_layout()
            fig.savefig(os.path.join(fig_dir,"failure_" + day.strftime('%Y%m%d') + "_" + str(freq) + "Hz.png"))
            plt.close()

        return True


