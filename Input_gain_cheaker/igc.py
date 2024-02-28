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

class Frame1(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master
        self.grid(row=0, column=0, sticky="nsew")
        self.select_api_widgets()

    def select_api_widgets(self):
        self.label1 = tk.Label(self)
        self.label1["text"] = "select sound class"
        self.label2 = tk.Label(self)
        self.label2["text"] = "select input device"

        api_list = [hostapi["name"] for hostapi in sd.query_hostapis()]
        self.combobox = ttk.Combobox(self,values=api_list,textvariable=tk.StringVar (),state="readonly",width=25)
        self.combobox.bind('<<ComboboxSelected>>', self.get_device)

        self.combobox2 = ttk.Combobox(self,textvariable=tk.StringVar(),state="readonly",width=25)

        self.button = tk.Button(self, text="OK",command=lambda: self.master.trangit_frame2(self.combobox.get(),self.combobox2.get()), height=2)

        self.label1.pack()
        self.combobox.pack(fill=tk.X)
        self.label2.pack()
        self.combobox2.pack(fill=tk.X)
        self.button.pack(fill=tk.X,pady=20)

    def get_device(self,event):
        self.combobox2.set('')
        api = self.combobox.get()
        devise_info = get_sound_device_api()
        device_list = []
        for devise in devise_info[api]:
            device_list.append(devise["name"])
        self.combobox2.config(values=device_list)

class Frame2(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.master = master

        self.fs = 44100
        self.downsample = 1
        self.signal_datatype = "float32"
        self.channels = 2
        self.rec_status = False
        self.level_buff = np.empty((1,2))
        self.level_disp_mean_sample = int(self.fs * 0.25)

        sd.default.samplerate = self.fs
        sd.default.channels = self.channels

        self.setting_widgets()

    def setting_widgets(self):

        # 波形プロット
        self.fig = self.init_wave_plot()
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH,
                                        expand=True)

        # 瞬時レベル表示
        self.lever_meter = tk.Frame(self)
        self.lever_meter.pack(pady=20)

        self.CH1_val = tk.StringVar(value="0")
        self.CH2_val = tk.StringVar(value="0")

        lb1 = tk.Label(self.lever_meter,text="ch1")
        lb2 = tk.Label(self.lever_meter,text="ch2")
        lb_dB1 = tk.Label(self.lever_meter, text='[dB] ')
        lb_dB2= tk.Label(self.lever_meter, text='[dB] ')

        self.CH1_disp = tk.Entry(self.lever_meter,width=5,bg="white",textvariable=self.CH1_val,fg="black")
        self.CH2_disp = tk.Entry(self.lever_meter,width=5,bg="white",textvariable=self.CH2_val,fg="black")

        lb1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.CH1_disp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb_dB1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.CH2_disp.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb_dB2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # スタートボタンその1
        self.button_text = tk.StringVar(value="Adjust start")
        self.adj_start_button = tk.Button(self.lever_meter, textvariable=self.button_text, command=self.adj_click)
        self.adj_start_button.pack(side=tk.LEFT,fill=tk.X)

        self.setting = tk.Frame(self)
        self.setting.pack(pady=20)

        lb3 = tk.Label(self.setting,text=" cal mean time ")
        lb4 = tk.Label(self.setting,text="[sec] ")
        self.mean_time_sec = tk.StringVar(value="5.0")
        self.set_mean_time = tk.Entry(self.setting,width=5,bg="white",textvariable=self.mean_time_sec,fg="black")

        self.cal_button_text = tk.StringVar(value="Check start")
        self.cal_start_button = tk.Button(self.setting, textvariable=self.cal_button_text,command=self.check_click)

        lb3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.set_mean_time.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        lb4.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.cal_start_button.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # device設定へ戻るボタン
        self.ret_button_text = tk.StringVar(value="Return device setting")
        self.ret_button = tk.Button(self, textvariable=self.ret_button_text, command=self.master.return_device_setting)
        self.ret_button.pack(side=tk.TOP,fill=tk.X)

    def init_wave_plot(self):
        fig = plt.figure(figsize=(5, 2),facecolor="#f0f0f0")
        self.ax1 = fig.add_subplot(2, 1, 1)
        self.ax2 = fig.add_subplot(2, 1, 2)
        self.length = int(1000 * self.fs / (1000 * self.downsample))
        self.plotdata = np.zeros((self.length,2))
        self.line1, = self.ax1.plot(self.plotdata[:,0],color="lightgreen")
        self.line2, = self.ax2.plot(self.plotdata[:,1],color="lightgreen")
        # ax1.axes.xaxis.set_visible(False)
        # ax2.axes.xaxis.set_visible(False)
        self.ax1.axes.xaxis.set_ticks([])
        self.ax2.axes.xaxis.set_ticks([])
        # ax1.axes.yaxis.set_ticks([])
        # ax2.axes.yaxis.set_ticks([])
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

        data = indata[::self.downsample]
        shift = len(data)
        self.plotdata = np.roll(self.plotdata, -shift, axis=0)
        self.plotdata[-shift:] = data

        self.level_buff = np.concatenate([self.level_buff,indata],axis=0)
        if len(self.level_buff) >= self.level_disp_mean_sample:
            with np.errstate(divide='ignore'):
                l1 = 10*np.log10(np.mean(np.abs(indata[:,0])))
                l2 = 10*np.log10(np.mean(np.abs(indata[:,1])))
            self.CH1_val.set(f"{l1:.2f}")
            self.CH2_val.set(f"{l2:.2f}")

            if l1 != -float('inf') and l2 != -float('inf') and np.abs(l1-l2) < 0.5:
                self.CH1_disp["bg"] ="lightgreen"
                self.CH2_disp["bg"] ="lightgreen"
            else:
                self.CH1_disp["bg"] ="orange"
                self.CH2_disp["bg"] ="orange"

            self.level_buff = np.empty((1,2))

    def update_plot(self, frame):
        self.line1.set_ydata(self.plotdata[:,0])
        self.line2.set_ydata(self.plotdata[:,1])
        return self.line1, self.line2

    def adj_click(self):
        if not self.rec_status:
            self.adj_start_button['state'] = 'disabled'
            self.ret_button['state'] =  'disabled'
            self.cal_start_button['state'] =  'disabled'

            self.stream = sd.InputStream(
            channels = self.channels,
            dtype =self.signal_datatype,
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
            self.ani = FuncAnimation(self.fig, self.update_plot, interval=50, blit=True,cache_frame_data=False)
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
        self.level_buff = np.empty((1,2))

    def check_click(self):
        try:
            mean_time = float(self.set_mean_time.get())
        except ValueError:
            messagebox.showerror("error", "数値を入力して下さい")
            return False

        if mean_time < 0 or mean_time > 100:
            messagebox.showerror("error", "0 < INPUT < 100")
            return False

        self.adj_start_button['state'] = 'disabled'
        self.ret_button['state'] =  'disabled'
        self.cal_start_button['state'] =  'disabled'
        self.cal_button_text.set("Wait...")
        self.update()

        recdata = sd.rec(int(mean_time * self.fs),channels = self.channels)
        sd.wait()

        # self.line1.remove()
        # self.line2.remove()
        # self.line1, = self.ax1.plot(recdata[:,0],color="magenta")
        # self.line2, = self.ax2.plot(recdata[:,1],color="magenta")
        # self.ax1.set_xlim([0, len(recdata)])
        # self.ax2.set_xlim([0, len(recdata)])
        # self.canvas.draw()
        # self.chack_status = True

        self.adj_start_button['state'] = 'normal'
        self.ret_button['state'] =  'normal'
        self.cal_start_button['state'] =  'normal'
        self.cal_button_text.set("Check start")
        self.master.trangit_frame3(recdata,self.fs)
        del recdata

class Frame3(tk.Frame):
    def __init__(self, recdata, fs, master=None):
        super().__init__(master)
        self.master = master
        self.recdata = recdata
        self.fs = fs
        self.setting_widgets()
        del self.recdata
        del self.fs
        del recdata
        del fs

    def setting_widgets(self):
        # 録音波形波形プロット
        self.fig = self.make_wave_chart()
        self.canvas = FigureCanvasTkAgg(self.fig, self)
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH,
                                        expand=True)

        ch1_L = cal_CPB_level(self.recdata[:,0], self.fs)
        ch2_L = cal_CPB_level(self.recdata[:,1], self.fs)
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
        self.ret_button = tk.Button(self, textvariable=self.ret_button_text, command=self.master.return_frame2)
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

class Root(tk.Tk):
    # 呪文
    def __init__(self):
        tk.Tk.__init__(self)
        self.title("sound gain check")
        self.geometry("400x400")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.frame1 = Frame1(self)
        self.frame1.grid(row=0, column=0, sticky="nsew")
        self.frame1.tkraise()

        self.protocol("WM_DELETE_WINDOW",self.quit_app)

    def trangit_frame2(self, api ,device_name):
        if api == '':
            messagebox.showerror("error", "please select soundclass")
        elif device_name == '':
            messagebox.showerror("error", "please select sound device")
        else:
            sd.default.device = get_sound_device_id(api ,device_name)
            self.frame2 = Frame2(self)
            self.frame2.grid(row=0, column=0, sticky="nsew")
            self.frame2.tkraise()

    def trangit_frame3(self,recdata,fs):
        self.frame3 = Frame3(recdata,fs ,master=self)
        self.frame3.grid(row=0, column=0, sticky="nsew")
        self.frame3.tkraise()

    def return_device_setting(self):
        self.frame1.tkraise()
        if "stream" in locals():
            self.frame2.stream.close()
        self.frame2.destroy()

    def return_frame2(self):
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
    for api_list in sd.query_hostapis():
        if api_list["name"] == api:
            api_devices_id = api_list["devices"]
    for id in d_buff:
        if id in api_devices_id:
            return id

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
    app = Root()
    app.mainloop()
=======
>>>>>>> 14f33755de067213ce573c9973f78f9d29d5d1d0
