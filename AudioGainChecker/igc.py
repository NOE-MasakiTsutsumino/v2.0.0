# -*- coding: utf-8 -*-
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import PIL.Image, PIL.ImageTk
import sounddevice as sd
import numpy as np
from matplotlib.animation import FuncAnimation
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import threading

class DeviceSetting(tk.Frame):
    """
    使用するapiとオーディオデバイスを選択させるための画面を表示するフレーム
    """
    def __init__(self, master=None):
        # ルート画面の設定継承
        super().__init__(master)
        self.master = master
        self.grid(row=0, column=0, sticky="nsew")
        # ウィジットの作成と配置
        self.setting_widgets()

    def setting_widgets(self):
        self.lb1 = tk.Label(self)
        self.lb1["text"] = "select sound class"
        self.lb2 = tk.Label(self)
        self.lb2["text"] = "select input device"

        # ホストマシンの使用可能なapi名リストを取得
        api_list = [hostapi["name"] for hostapi in sd.query_hostapis()]
        # apiの選択リストウィジットを作成
        self.api_selecter = ttk.Combobox(self,values=api_list,textvariable=tk.StringVar (),state="readonly",width=25)
        # 値が選択されたら使用可能なオーディオデバイスのリストを取得するイベント起動
        self.api_selecter.bind('<<ComboboxSelected>>', self.get_device)
        # オーディオデバイスの選択リストウィジットを作成
        self.device_selecter = ttk.Combobox(self,textvariable=tk.StringVar(),state="readonly",width=25)

        # 選択されたapiとdevice名を返して次の画面に遷移するボタン
        self.button = tk.Button(self, text="OK",command=lambda: self.master.trangit_InputMoniter(self.api_selecter.get(),self.device_selecter.get()), height=2)

        # ウィジット配置
        self.lb1.pack()
        self.api_selecter.pack(fill=tk.X)
        self.lb2.pack()
        self.device_selecter.pack(fill=tk.X)
        self.button.pack(fill=tk.X,pady=20)

    def get_device(self,event):
        """api_selecterの値選択時に使用可能なオーディオデバイスを取得する
        Args:
            event (_type_): api_selecterの値選択時に発生するイベント
        """
        self.device_selecter.set('')
        api = self.api_selecter.get()
        devise_info = get_sound_device_api()
        device_list = []
        for devise in devise_info[api]:
            device_list.append(devise["name"])
        self.device_selecter.config(values=device_list)

class InputMoniter(tk.Frame):
    """
    入力波形とレベルを表示してマイクの感度を調整するための画面
    """
    def __init__(self, master=None):
        # ルート画面の設定継承
        super().__init__(master)
        self.master = master
        self.rec_status: bool = False

        # ウィジットの作成と配置
        self.setting_widgets()

    def setting_widgets(self):

        #　入力波形表示ウィジット
        self.fig = self.init_wave_plot()
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH,
                                        expand=True)

        # 瞬時レベル表示ウィジット
        self.lever_meter = tk.Frame(self)
        self.lever_meter.pack(pady=20)

        # 初期値
        self.ch1_val = tk.StringVar(value="0")
        self.ch2_val = tk.StringVar(value="0")

        lb1 = tk.Label(self.lever_meter,text="ch1")
        lb2 = tk.Label(self.lever_meter,text="ch2")
        lb_dB1 = tk.Label(self.lever_meter, text='[dB] ')
        lb_dB2= tk.Label(self.lever_meter, text='[dB] ')

        self.ch1_disp = tk.Entry(self.lever_meter,width=5,bg="white",textvariable=self.ch1_val,fg="black")
        self.ch2_disp = tk.Entry(self.lever_meter,width=5,bg="white",textvariable=self.ch2_val,fg="black")

        # ウィジット配置
        lb1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.ch1_disp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb_dB1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.ch2_disp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb_dB2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # リアルタイム表示スタートボタン
        self.button_text = tk.StringVar(value="Adjust start")
        self.adj_start_button = tk.Button(self.lever_meter, textvariable=self.button_text, command=self.adj_click)
        self.adj_start_button.pack(side=tk.LEFT,fill=tk.X)

        # レベル表示平均化時間設定ウィジット
        self.lv_disp_setting = tk.Frame(self)
        self.lv_disp_setting.pack(pady=20)

        lb3 = tk.Label(self.lv_disp_setting,text=" level mean time ")
        lb4 = tk.Label(self.lv_disp_setting,text="[sec] ")
        self.lv_mean_sec_val = tk.StringVar(value="0.3")
        self.set_lv_mean_sec = tk.Entry(self.lv_disp_setting,width=5,bg="white",textvariable=self.lv_mean_sec_val,fg="black")

        lb3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.set_lv_mean_sec.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb4.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # check平均化時間設定ウィジット
        self.cal_mean_setting = tk.Frame(self)
        self.cal_mean_setting.pack(pady=20)

        lb5 = tk.Label(self.cal_mean_setting,text=" cal mean time ")
        lb6 = tk.Label(self.cal_mean_setting,text="[sec] ")
        self.cal_mean_sec = tk.StringVar(value="5.0")
        self.set_cal_mean_sec = tk.Entry(self.cal_mean_setting,width=5,bg="white",textvariable=self.cal_mean_sec,fg="black")

        self.cal_button_text = tk.StringVar(value="Check start")
        self.cal_start_button = tk.Button(self.cal_mean_setting, textvariable=self.cal_button_text,command=self.check_click)

        lb5.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.set_cal_mean_sec.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb6.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.cal_start_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # device設定へ戻るボタン
        self.ret_button_text = tk.StringVar(value="Return device setting")
        self.ret_button = tk.Button(self, textvariable=self.ret_button_text, command=self.master.return_DeviceSetting)
        self.ret_button.pack(side=tk.TOP,fill=tk.X)

    def init_wave_plot(self):
        fig = plt.figure(figsize=(5, 2),facecolor="#f0f0f0")
        self.ax1 = fig.add_subplot(2, 1, 1)
        self.ax2 = fig.add_subplot(2, 1, 2)
        self.length = int(sd.default.samplerate)
        self.plotdata = np.zeros((self.length,2))
        self.line1, = self.ax1.plot(self.plotdata[:,0],color="lightgreen")
        self.line2, = self.ax2.plot(self.plotdata[:,1],color="lightgreen")
        self.ax1.axes.xaxis.set_ticks([])
        self.ax2.axes.xaxis.set_ticks([])
        self.ax1.set_facecolor("gray")
        self.ax2.set_facecolor("gray")
        self.ax1.set_ylabel("ch1 signal")
        self.ax2.set_ylabel("ch2 signal")
        self.ax1.set_ylim([-1, 1])
        self.ax2.set_ylim([-1, 1])
        self.ax1.set_xlim([0, self.length])
        self.ax2.set_xlim([0, self.length])
        self.ax1.yaxis.grid(True)
        self.ax2.yaxis.grid(True)
        fig.tight_layout()

        return fig

    def callback(self, indata, frames, time, status):

        data = indata[::1]
        shift = len(data)
        self.plotdata = np.roll(self.plotdata, -shift, axis=0)
        self.plotdata[-shift:] = data

        self.level_buff.extend(indata)
        self.indata_len_count += len(indata)

        if self.indata_len_count >= self.lv_mean_sec:
            level = np.array(self.level_buff)
            # # 0除算で出してくる警告は無視する
            with np.errstate(divide='ignore'):
                level = 10*np.log10(np.mean(np.abs(level),axis=0))
            # レベル表示の値を更新
            self.ch1_val.set(f"{level[0]:.2f}")
            self.ch2_val.set(f"{level[1]:.2f}")
            # 配列初期化
            self.level_buff.clear()
            self.indata_len_count = 0

            if level[0] != -float('inf') and level[1] != -float('inf'):
                if np.abs(level[0]-level[1]) < 0.3:
                    self.ch1_disp["bg"] ="lightgreen"
                    self.ch2_disp["bg"] ="lightgreen"
                else:
                    self.ch1_disp["bg"] ="orange"
                    self.ch2_disp["bg"] ="orange"

    def update_plot(self, frame):
        self.line1.set_ydata(self.plotdata[:,0])
        self.line2.set_ydata(self.plotdata[:,1])
        return self.line1, self.line2

    def adj_click(self):
        try:
            self.lv_mean_sec = float(self.lv_mean_sec_val.get())*sd.default.samplerate
        except ValueError:
            messagebox.showerror("error", "数値を入力して下さい")
            return False

        if self.lv_mean_sec <= 0 or self.lv_mean_sec > 3*sd.default.samplerate:
            messagebox.showerror("error", "0 < level mean time < 3")
            return False

        if not self.rec_status:
            self.adj_start_button['state'] = 'disabled'
            self.ret_button['state'] =  'disabled'
            self.cal_start_button['state'] =  'disabled'
            self.set_lv_mean_sec['state'] =  'disabled'
            self.set_cal_mean_sec['state'] =  'disabled'

            self.level_buff = []
            self.indata_len_count = 0
            self.stream = sd.InputStream(
            callback =self.callback)

            thread = threading.Thread(target=self.adj_on)
            thread.start()
        else:
            self.adj_start_button['state'] = 'disabled'
            self.ret_button['state'] =  'disabled'
            self.cal_start_button['state'] =  'disabled'
            thread = threading.Thread(target=self.adj_off)
            thread.start()

    def adj_on(self):
        self.rec_status = True
        self.button_text.set("Adjust stop")
        self.stream.start()
        self.ani = FuncAnimation(self.fig, self.update_plot, interval=250, blit=True,cache_frame_data=False)
        self.adj_start_button['state'] = 'normal'

    def adj_off(self):
        self.ani.event_source.stop()
        self.stream.abort()
        self.stream.close()
        self.plotdata = np.zeros((self.length,2))
        self.button_text.set("Adjust start")
        self.rec_status = False
        self.adj_start_button['state'] = 'normal'
        self.ret_button['state'] =  'normal'
        self.cal_start_button['state'] =  'normal'
        self.set_lv_mean_sec['state'] =  'normal'
        self.set_cal_mean_sec['state'] =  'normal'

    def check_click(self):
        try:
            mean_time = float(self.set_cal_mean_sec.get())
        except ValueError:
            messagebox.showerror("error", "数値を入力して下さい")
            return False

        if mean_time < 1 or mean_time > 30:
            messagebox.showerror("error", "1 <= cal mean time <= 30")
            return False

        self.adj_start_button['state'] = 'disabled'
        self.ret_button['state'] =  'disabled'
        self.cal_start_button['state'] =  'disabled'
        self.cal_button_text.set("Wait...")
        self.update()
        mean_time = int(mean_time * sd.default.samplerate)
        recdata = sd.rec(mean_time)
        sd.wait()

        self.adj_start_button['state'] = 'normal'
        self.ret_button['state'] =  'normal'
        self.cal_start_button['state'] =  'normal'
        self.cal_button_text.set("Check start")
        self.master.trangit_DispCheckResult(recdata)
        del recdata

class DispCheckResult(tk.Frame):
    def __init__(self, recdata, master=None):
        super().__init__(master)
        self.master = master
        self.recdata = recdata
        self.setting_widgets()
        del self.recdata
        del recdata

    def setting_widgets(self):
        # 録音波形波形プロット
        self.fig = self.make_wave_chart()
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH,
                                        expand=True)

        ch1_L = cal_CPB_level(self.recdata[:,0], sd.default.samplerate)
        ch2_L = cal_CPB_level(self.recdata[:,1],sd.default.samplerate)
        diff_L = [x - y if x - y > 0 else x - y for x, y in zip(ch1_L, ch2_L)]

        self.disp_result = tk.Frame(self)
        self.disp_result.pack(side=tk.TOP)

        # label
        self.label = tk.Frame(self.disp_result)
        self.label.pack(side=tk.LEFT)

        lb0 = tk.Label(self.label,text="")
        lb1 = tk.Label(self.label,text="diff")
        lb2 = tk.Label(self.label,text="ch1")
        lb3 = tk.Label(self.label,text="ch2")

        lb0.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        lb1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        lb2.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        lb3.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 250Hz
        self.c1 = tk.Frame(self.disp_result)
        self.c1.pack(side=tk.LEFT)

        lb250 = tk.Label(self.c1,text="250")
        disp_diff = tk.Entry(self.c1,width=5,bg="white",fg="black")
        disp_ch1 = tk.Entry(self.c1,width=5,bg="white",fg="black")
        disp_ch2 = tk.Entry(self.c1,width=5,bg="white",fg="black")
        disp_diff.insert(tk.END,f"{diff_L[0]:.2f}")
        disp_ch1.insert(tk.END,f"{ch1_L[0]:.2f}")
        disp_ch2.insert(tk.END,f"{ch2_L[0]:.2f}")

        lb250.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_diff.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch2.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 500Hz
        self.c2 = tk.Frame(self.disp_result)
        self.c2.pack(side=tk.LEFT)

        lb500 = tk.Label(self.c2,text="500")
        disp_diff = tk.Entry(self.c2,width=5,bg="white",fg="black")
        disp_ch1 = tk.Entry(self.c2,width=5,bg="white",fg="black")
        disp_ch2 = tk.Entry(self.c2,width=5,bg="white",fg="black")
        disp_diff.insert(tk.END,f"{diff_L[1]:.2f}")
        disp_ch1.insert(tk.END,f"{ch1_L[1]:.2f}")
        disp_ch2.insert(tk.END,f"{ch2_L[1]:.2f}")

        lb500.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_diff.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch2.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 1000Hz
        self.c3 = tk.Frame(self.disp_result)
        self.c3.pack(side=tk.LEFT)

        lb1000 = tk.Label(self.c3,text="1000")
        disp_diff = tk.Entry(self.c3,width=5,bg="white",fg="black")
        disp_ch1 = tk.Entry(self.c3,width=5,bg="white",fg="black")
        disp_ch2 = tk.Entry(self.c3,width=5,bg="white",fg="black")
        disp_diff.insert(tk.END,f"{diff_L[2]:.2f}")
        disp_ch1.insert(tk.END,f"{ch1_L[2]:.2f}")
        disp_ch2.insert(tk.END,f"{ch2_L[2]:.2f}")

        lb1000.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_diff.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch2.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 2000Hz
        self.c4 = tk.Frame(self.disp_result)
        self.c4.pack(side=tk.LEFT)

        lb2000 = tk.Label(self.c4,text="2000")
        disp_diff = tk.Entry(self.c4,width=5,bg="white",fg="black")
        disp_ch1 = tk.Entry(self.c4,width=5,bg="white",fg="black")
        disp_ch2 = tk.Entry(self.c4,width=5,bg="white",fg="black")
        disp_diff.insert(tk.END,f"{diff_L[3]:.2f}")
        disp_ch1.insert(tk.END,f"{ch1_L[3]:.2f}")
        disp_ch2.insert(tk.END,f"{ch2_L[3]:.2f}")

        lb2000.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_diff.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch2.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # 2000Hz
        self.c5 = tk.Frame(self.disp_result)
        self.c5.pack(side=tk.LEFT)

        lb4000 = tk.Label(self.c5,text="4000")
        disp_diff = tk.Entry(self.c5,width=5,bg="white",fg="black")
        disp_ch1 = tk.Entry(self.c5,width=5,bg="white",fg="black")
        disp_ch2 = tk.Entry(self.c5,width=5,bg="white",fg="black")
        disp_diff.insert(tk.END,f"{diff_L[4]:.2f}")
        disp_ch1.insert(tk.END,f"{ch1_L[4]:.2f}")
        disp_ch2.insert(tk.END,f"{ch2_L[4]:.2f}")

        lb4000.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_diff.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch2.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # AP
        self.c6 = tk.Frame(self.disp_result)
        self.c6.pack(side=tk.LEFT)

        lbAP = tk.Label(self.c6,text="AP")
        disp_diff = tk.Entry(self.c6,width=5,bg="white",fg="black")
        disp_ch1 = tk.Entry(self.c6,width=5,bg="white",fg="black")
        disp_ch2 = tk.Entry(self.c6,width=5,bg="white",fg="black")
        disp_diff.insert(tk.END,f"{diff_L[5]:.2f}")
        disp_ch1.insert(tk.END,f"{ch1_L[5]:.2f}")
        disp_ch2.insert(tk.END,f"{ch2_L[5]:.2f}")

        lbAP.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_diff.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch1.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        disp_ch2.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        # frame2へ戻るボタン
        self.ret_button_text = tk.StringVar(value="Return adjust moniter")
        self.ret_button = tk.Button(self, textvariable=self.ret_button_text, command=self.master.return_InputMoniter)
        self.ret_button.pack(side=tk.BOTTOM,fill=tk.X)

    def make_wave_chart(self):
        fig = plt.figure(figsize=(5, 1.5),facecolor="#f0f0f0")
        self.ax1 = fig.add_subplot(2, 1, 1)
        self.ax2 = fig.add_subplot(2, 1, 2)
        self.length = len(self.recdata)
        self.plotdata = np.zeros((self.length,2))
        self.line1, = self.ax1.plot(self.recdata[:,0],color="magenta")
        self.line2, = self.ax2.plot(self.recdata[:,1],color="magenta")
        self.ax1.axes.xaxis.set_ticks([])
        self.ax2.axes.xaxis.set_ticks([])
        self.ax1.set_facecolor("gray")
        self.ax2.set_facecolor("gray")
        self.ax1.set_ylabel("ch1 signal")
        self.ax2.set_ylabel("ch2 signal")
        self.ax1.set_ylim([-1, 1])
        self.ax2.set_ylim([-1, 1])
        self.ax1.set_xlim([0, self.length])
        self.ax2.set_xlim([0, self.length])
        self.ax1.yaxis.grid(True)
        self.ax2.yaxis.grid(True)
        fig.tight_layout()

        return fig

class ApplicationRoot(tk.Tk):

    def __init__(self):
        # ウィンドウの共通設定
        tk.Tk.__init__(self)
        self.title("sound gain check")
        self.geometry("400x500")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ×ボタンがクリックされた際の処理を定義
        self.protocol("WM_DELETE_WINDOW",self.quit_app)

        # 最初にデバイス選択画面を表示
        self.frame1 = DeviceSetting(self)
        self.frame1.grid(row=0, column=0, sticky="nsew")
        self.frame1.tkraise()

    def trangit_InputMoniter(self, api ,device_name):
        if api == '':
            messagebox.showerror("error", "please select soundclass")
        elif device_name == '':
            messagebox.showerror("error", "please select sound device")
        else:
            sd.default.device, sd.default.samplerate = get_sound_device_id(api ,device_name)
            self.frame2 = InputMoniter(self)
            self.frame2.grid(row=0, column=0, sticky="nsew")
            self.frame2.tkraise()

    def trangit_DispCheckResult(self,recdata):
        self.frame3 = DispCheckResult(recdata,master=self)
        self.frame3.grid(row=0, column=0, sticky="nsew")
        self.frame3.tkraise()

    def return_DeviceSetting(self):
        self.frame1.tkraise()
        if "stream" in locals():
            self.frame2.stream.close()
        self.frame2.destroy()

    def return_InputMoniter(self):
        self.frame2.tkraise()
        self.frame3.destroy()

    def quit_app(self):
            self.quit()
            self.destroy()

def get_sound_device_id(api ,device_name):
    d_buff = []
    for device in sd.query_devices():
        if device["name"] == device_name:
            d_buff.append(device["index"])
            samplelate = device["default_samplerate"]
    for api_list in sd.query_hostapis():
        if api_list["name"] == api:
            api_devices_id = api_list["devices"]
    for id in d_buff:
        if id in api_devices_id:
            return id, samplelate

    return False

def get_sound_device_api():
    di = {}
    for hostapi in sd.query_hostapis():
        hostapi_name = hostapi["name"]
        di[hostapi_name] =[]
        for device_numbar in hostapi["devices"]:
            device = sd.query_devices(device = device_numbar)
            max_in_ch  = device["max_input_channels"]
            if max_in_ch >= 2:
                di[hostapi_name].append(device)

    return di

def get_sound_device_name_list():
    ret=[]
    for device in sd.query_devices():
        if device["max_input_channels"] >= 2:
            ret.append(device["name"])
    return ret

def cal_CPB_level(recdata, fs):

    tap = 1024
    overlap_rate = 0.5
    hop_len = int(tap * overlap_rate)
    window = np.hamming(tap)
    rfft = np.fft.rfft

    oct_freq_masks = {}
    ceter_freqs = [250,500,1000,2000,4000]
    for freq in ceter_freqs:
        oct_freq_l = freq / 2**(1 / 2)
        oct_freq_h = freq * 2**(1 / 2)
        fft_f = np.fft.rfftfreq(tap, 1 / fs)
        mask = np.array([(fft_f >= oct_freq_l) & (fft_f < oct_freq_h)])
        oct_freq_masks[str(freq)] = mask.reshape([-1,1])

    frame_num = int(np.floor((recdata.shape[0] - tap) / hop_len)) + 1
    if frame_num < 1:
        msg = f"録音時間がFFTタップ数[{tap}]に満たない"
        messagebox.showerror("error", msg)
        return False

    f=[]
    for i in range(frame_num):
        frame = window * recdata[(hop_len * i):(tap + (hop_len * i))]
        f.append(rfft(frame, axis=0))

    S = (np.mean(np.abs(f), axis=0))
    ret = []
    for freq in ceter_freqs:
        ret.append(10*np.log10(np.sum(S[oct_freq_masks[str(freq)][:,0]], axis=0)))

    ret.append(10*np.log10(np.sum(S, axis=0)))

    return ret

if __name__ == "__main__":
    sd.default.channels = 2
    sd.default.dtype =  "float32"
    app = ApplicationRoot()
    app.mainloop()