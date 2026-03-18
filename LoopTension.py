#
# class to loop over tension measurements
#
import matplotlib.animation as animation
from collections import deque
import sys
import numpy as np
from numpy.fft import fft, fftfreq, rfft, irfft
from numpy import argmax, sqrt, mean, diff, log
import matplotlib
import matplotlib.pyplot as plt
import math, time, os
import scipy
from scipy.signal import fftconvolve
from scipy.signal.windows import blackmanharris
from parabolic import parabolic
import serial
import serial.tools.list_ports
import math, time, os

class LoopTension(object):
    def __init__(self, wirelen=0.65, max_points=100): # wire length in m
        print("Initializing tension measurement for wire length",wirelen)
        self.fscale = 3.79e-3 * wirelen*wirelen # scale between frequency and wire length, computed using g, W density, wire diameter
        self.nomtension = 80 # nominal tension (gm)
        self.tensionprecision = 2 # measurement precision: The goal is to get the tension to nominal within this
        self.maxtension = 100 # maximum tension when conditioning the wire
        self.breaktension = 120 # breaking point!
        self.SamplingPeriod = 3e-4 # initial estimate of sampling period
        self.nADC = 400          # Must match DataLength in the Arduino code
        self.ADC = np.zeros(self.nADC)
        self.FFT = np.zeros(self.nADC)
        # Find the arduino
        ports = [p.device for p in serial.tools.list_ports.comports()
                 if 'VID:PID=2341:003D' in p.hwid]
        if len(ports)<1:
            print('Arduino not found \nPlug wire tensioner into any USB port')
            time.sleep(2)
            print("Exiting script")
            sys.exit()
        print("Arduino Due at {}".format(ports[0]))
        self.portloc = ports[0]
        self.ser = serial.Serial(port=self.portloc, baudrate=115200)
        time.sleep(1)
        digifreq = 1.0/self.SamplingPeriod
        print(f"Initial digitization frequency = {digifreq:.2f}")


        #Gemini code
        self.max_points = max_points
        self.running = True
        self.tare_offset = 0.0
        self.data_log = []

        self.tension_history = deque([self.nomtension] * max_points, maxlen=max_points)
        self.time_history = deque([0.0] * max_points, maxlen=max_points)
        self.start_time = time.time()

        # Create Layout: 2 rows, 2 columns
        # Top spans both columns, bottom is split
        self.fig = plt.figure(figsize=(12, 10))
        self.ax_chart = plt.subplot2grid((3, 2), (0, 0), colspan=2)
        self.ax_wave = plt.subplot2grid((3, 2), (1, 0))
        self.ax_fft = plt.subplot2grid((3, 2), (1, 1))
        plt.subplots_adjust(hspace=0.4, bottom=0.15)

        # 1. Main Strip Chart Setup
        self.line_tension, = self.ax_chart.plot([], [], 'b-', lw=2)
        self.ax_chart.axhline(y=self.nomtension, color='green', linestyle='--', alpha=0.5, label='Nominal')
        self.ax_chart.axhline(y=self.breaktension, color='red', linestyle='-', alpha=0.8, label='BREAK')
        self.ax_chart.set_title("Real-time Tension History")
        self.ax_chart.set_ylabel("Tension (gm)")

        # 2. Waveform Plot Setup
        self.line_wave, = self.ax_wave.plot([], [], 'k-', lw=1)
        self.ax_wave.set_title("Latest Raw Waveform")
        self.ax_wave.set_xlabel("Time (ms)")

        # 3. FFT Plot Setup
        self.line_fft, = self.ax_fft.plot([], [], 'm-')
        self.ax_fft.set_title("Power Spectrum (FFT)")
        self.ax_fft.set_xlabel("Frequency (Hz)")
        self.ax_fft.set_xlim(0, 500) # Typical range for these wires

        # Buttons
        ax_stop = plt.axes([0.8, 0.02, 0.1, 0.05])
        ax_tare = plt.axes([0.65, 0.02, 0.1, 0.05])
        self.btn_stop = Button(ax_stop, 'Stop & Save', color='lightcoral')
        self.btn_tare = Button(ax_tare, 'Tare', color='lightblue')
        self.btn_stop.on_clicked(self.stop_measurement)
        self.btn_tare.on_clicked(self.tare_tension)

        print("initialized\n")


    def tare_tension(self, event):
        if len(self.tension_history) > 0:
            self.tare_offset = self.tension_history[-1]
            print(f"Tared at {self.tare_offset:.2f} gm")

    def stop_measurement(self, event):
        self.running = False
        self.save_to_csv()
        if self.ser.is_open: self.ser.close()
        plt.close(self.fig)

    def save_to_csv(self):
        filename = f"tension_log_{int(time.time())}.csv"
        if self.data_log:
            with open(filename, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=self.data_log[0].keys())
                writer.writeheader()
                writer.writerows(self.data_log)
            print(f"Saved to {filename}")

    def update_plot(self, frame):
        if not self.running: return self.line_tension, self.line_wave, self.line_fft
        iperiod = self.period(self.nomtension)
        if len(self.tension_history) > 0:
            iperiod = self.period(self.tension_history[-1])

        p_width = 0.5 * iperiod
        self.PulseAndRead(p_width * 1e6, False)

        freq = self.frequency()
        tension = self.tension_gm(freq) - self.tare_offset
        ts = time.time() - self.start_time

        # Update History
        self.tension_history.append(tension)
        self.time_history.append(ts)
        self.data_log.append({'time': ts, 'tension': tension, 'freq': freq})

        # Update Strip Chart
        self.line_tension.set_data(self.time_history, self.tension_history)
        self.ax_chart.set_xlim(self.time_history[0], self.time_history[-1] + 0.2)

        # Update Waveform (Current self.ADC)
        wave_x = np.linspace(0, self.nADC * self.SamplingPeriod * 1000, self.nADC)
        self.line_wave.set_data(wave_x, self.ADC)
        self.ax_wave.relim()
        self.ax_wave.autoscale_view()

        # Update FFT
        xf = rfftfreq(self.nADC, self.SamplingPeriod)
        self.line_fft.set_data(xf, np.abs(self.FFT))
        self.ax_fft.set_ylim(0, np.max(np.abs(self.FFT)) * 1.1)

        return self.line_tension, self.line_wave, self.line_fft

    def run_realtime_chart(self):
        self.ani = animation.FuncAnimation(self.fig, self.update_plot, interval=50, blit=False)
        plt.show()

    def tension_gm(self,freq):
        # compute the tension in gm equivalent given the frequency in Hz
        return self.fscale*freq*freq

    def period(self,tension_gm): # return period in seconds for a given tension in gm
        return np.sqrt(self.fscale/tension_gm)

    def plotWaveform(self):
        fig, (timed,freqd) = plt.subplots(2,1,layout='constrained', figsize=(20,10))
        nsamp = self.nADC
        tstep = self.SamplingPeriod
        start = 0.
        stop = nsamp*tstep
        timeline = timed.plot(np.arange(start,stop,tstep),self.ADC,scalex=True,scaley=True)
        timed.set_xlabel("Time (seconds)")
        timed.set_ylabel("Signal (ADC)")
        nplot = 100
        xf = fftfreq(nsamp,self.SamplingPeriod)[1:int(nsamp/2)] # omit 0th (static) and negative frequencies
        absfft = abs(self.FFT[1:int(nsamp/2)])
        freqplt =freqd.semilogy(xf[0:nplot], absfft[0:nplot])
        freqd.set_xlabel("Frequency (Hz)")
        freqd.set_ylabel("Amplitude")

    def frequency(self):
        # window
        nsamp = len(self.ADC)
        windowed = self.ADC * blackmanharris(nsamp)
        self.FFT = rfft(windowed)
    # Find the peak (primary harmonic) and interpolate around it to get a more accurate peak
        absfft = abs(self.FFT[1:int(nsamp/2)]) # skip 0th and negative frequencies
        i = argmax(absfft)
        true_i = parabolic(log(absfft), i)[0] # parabol maximum
        # convert to sampling frequency in Hz
        freq = true_i / (len(windowed)*self.SamplingPeriod)
        return freq

    def PulseAndRead(self, pulse_width, printit):
        # Trigger the Arduino to take data
        self.ser.write(b'5\n')
        # Write the current pulse width; To effect maximum energy transfer this should be 1/2 the primary period.
        # if the pulse is >> period the energy transfer will zero out
        # If the initial tension is low, the period is long, this will still produce a signal, and self-correct on subsequent reads
        self.ser.write(bytes(str(int(pulse_width))+'\n','UTF-8'))
        self.ser.readline()  # Read in the line where Arduino echos this back
        # Read in the line where Arduino prints the pulse width, and print it out once per iteration
        mess = str(self.ser.readline())
        if(printit):
            print (mess)
        for ic in range(0, self.nADC-1):
            line = int(self.ser.readline())
            if line >= 8192: # 8192 = 2^13: sign bit in the ADC?
                val = (line-16383)*1.22
            else:
                val = (line+1)*1.22 # where does this factor come from? it doesn't change frequency so not important
            self.ADC[ic] = float(val)

        # read the duration; this gives the absolute scale of the sampling frequency
        elapsed = int(self.ser.readline())*1e-6
        #print(f"Elapsed time = {elapsed:.5f} seconds")
        digifreq = self.nADC/elapsed
        self.SamplingPeriod = elapsed/self.nADC
        #print(f"Measured digitization frequency = {digifreq:.2f}")

    def print_tension(self,npulses):
        print("Printing tension in a Loopg over",npulses,"pulses")
        # set initial pulse width according to the nominal tension
        iperiod = self.period(self.nomtension)
        ifreq = 1.0/iperiod
        pulse_width = 0.5*iperiod # maximum energy transfer with 1/2 period
        #print(f"Initial frequency = {ifreq:.1f} Hz, pulse width = {pulse_width:.6f} seconds")
        for ik in range(0, npulses):
            self.PulseAndRead(pulse_width*1e6,ik==0) # microseconds
            freq = self.frequency()
            if(freq*self.SamplingPeriod < 0.5):
                # convert to a tension
                tension = self.tension_gm(freq)
                 print(f"Measured fundamental frequency {freq:.1f} Hz, corresponding to a tension of {tension:.1f} gm")
            # update the pulse width
                0.5*self.period(tension)
            else:
                print(f"Failed frequency measurement {freq:.1f} Hz")

