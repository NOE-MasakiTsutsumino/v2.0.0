from matplotlib import pyplot as plt
import os

def draw_sensitivity_histogram(stid, freq, params, mean, lower, upper, tolerance, dir, day):
    """
    結果分析用のヒストグラム画像作成
    """

    fig_dir = os.path.join(dir,day.strftime('%Y%m%d'))
    if not os.path.exists(fig_dir):
        os.makedirs(fig_dir)

    fig = plt.figure()
    ax = fig.add_subplot()

    plt.hist(params,alpha = 0.5, bins = 10)
    plt.axvline(mean, color='blue', linestyle='dashed', linewidth=1)
    plt.axvspan(lower, upper, color="skyblue",alpha = 0.3)

    if tolerance != 0:
        plt.axvspan(lower - tolerance, lower, color="lightgreen",alpha = 0.3)
        plt.axvspan(upper, upper + tolerance, color="lightgreen",alpha = 0.3)

    # plt.legend(loc='upper left')
    plt.text(0.5,-0.1, "[mean = " + str(f'{mean:.2g}') + "]",horizontalalignment="center",transform=ax.transAxes)
    plt.xlim([-1.5,1.5])
    plt.grid()
    # plt.tight_layout()
    plt.title(f"{stid} - {freq}Hz")

    fig.savefig(os.path.join(fig_dir,day.strftime('%Y%m%d') + "_" + str(freq) + "Hz.png"))
    plt.close()

    return fig