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
    def __init__(self,wirelen=0.65): # wire length in m
        print("Initializing tension measurement for wire length",wirelen)
        self.fscale = 3.79e-3 * wirelen*wirelen # scale between frequency and wire length, computed using g, W density, wire diameter
        self.nomtension = 80 # nominal tension (gm)
        self.maxtension = 100 # maximum tension when conditioning the wire
        self.breaktension = 120 # breaking point!
        self.SamplingPeriod = 3e-4 # initial estimate of sampling period
        self.nADC = 400          # Should match DataLength in the Arduino code
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
        print("initialized\n")

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
        # Write the desired pulse width
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

        # read the duration; this gives the sample frequency
        elapsed = int(self.ser.readline())*1e-6
        print(f"Elapsed time = {elapsed:.5f} seconds")
        digifreq = self.nADC/elapsed
        self.SamplingPeriod = elapsed/self.nADC
        print(f"Measured digitization frequency = {digifreq:.2f}")

    def loop(self,npulses):
        print("Looping over",npulses,"pulses")
        # set initial pulse width according to the nominal tension
        iperiod = self.period(self.nomtension)
        ifreq = 1.0/iperiod
        pulse_width = 0.5*iperiod # maximum energy transfer with 1/2 period
        print(f"Initial frequency = {ifreq:.1f} Hz, pulse width = {pulse_width:.6f} seconds")
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

