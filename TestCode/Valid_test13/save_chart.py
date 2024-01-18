from matplotlib import pyplot as plt
import os

def draw_sensitivity_histogram(cal, stid, freq, params, mean, m_lower, m_upper, n_lower, n_upper, tolerance_lower, tolerance_upper, dir, day):
    """
    結果分析用のヒストグラム画像作成
    """

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
    plt.legend([f"mean = {str(f'{mean:.2g}')}", f"norm_interval = {n_lower:.2g} to {n_upper:.2g}", f"tolerance = {tolerance_lower + n_lower:.2g} to {tolerance_upper + n_upper:.2g}"], loc='upper left')
    plt.text(0.5,-0.1, f"[Internal_cal ={cal}]",horizontalalignment="center",transform=ax.transAxes)
    plt.xlim([-1.5,1.5])
    plt.grid()
    plt.title(f"{stid} - {freq}Hz")
    plt.tight_layout()

    fig.savefig(os.path.join(fig_dir,day.strftime('%Y%m%d') + "_" + str(freq) + "Hz.png"))
    plt.close()

    return fig