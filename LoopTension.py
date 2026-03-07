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
from datetime import datetime as dt

class LoopTension(object):
    def __init__(self,wirelen=0.65): # wire length in m
        self.wirelen = wirelen
        self.fscale = 3.864e-3 * wirelen*wirelen # scale between frequency and wire length
        self.nomtension = 80 # nominal tension
        self.maxtension = 100 # maximum tension when conditioning the wire
        self.breaktension = 120 # breaking point!
        self.ArduinoPeriod = 1./8900. # effective period
        self.nplot = 200
        self.nmax = 400
        self.nADC = 2000          # Should match DataLength in the Arduino code
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
        print("initialized\n")

    def tension_gm(self,freq):
        # compute the tension in gm equivalent given the frequency in Hz
        return self.fscale*freq*freq

    def period(self,tension_gm): # return period in seconds for a given tension in gm
        return self.wirelen*np.sqrt(self.fscale/tension_gm)

    def plot(self):
        fig, (timed,freqd) = plt.subplots(2,1,layout='constrained', figsize=(20,10))
        nsamp = len(self.ADC)
        tstep = self.ArduinoPeriod
        start = 0.
        stop = nsamp*tstep
        timeline = timed.plot(np.arange(start,stop,tstep),self.ADC,scalex=True,scaley=True)
        timed.set_xlabel("Time (seconds)")
        timed.set_ylabel("Signal (ADC)")
        nplot = 400
        xf = fftfreq(nsamp,self.ArduinoPeriod)[:nsamp//2]
        freqplt =freqd.semilogy(xf[1:nplot//2], 2.0/nplot * np.abs(self.FFT[1:nplot//2]), '-r')
        freqd.set_xlabel("Frequency (Hz)")
        freqd.set_ylabel("Amplitude")

    def frequency(self):
        # compute the sampling frequency in KHz
        nsamp = len(self.ADC)
        windowed = self.ADC * blackmanharris(nsamp)
        self.FFT = fft(windowed)
        #print(windowed)
    # Find the peak (primary harmonic) and interpolate around it to get a more accurate peak
        nmax = 400
        i = argmax(abs(self.FFT[:nmax]))
        true_i = parabolic(log(abs(self.FFT)), i)[0]
        # compute the sampling frequency in Hz
        ffreq = true_i / (len(windowed)*self.ArduinoPeriod)
        return ffreq

    def PulseAndRead(self, pulse_width, printit):
        # Trigger the Arduino to take data
        self.ser.write(b'5\n')
        # Write the desired pulse width
        self.ser.write(bytes(str(int(pulse_width))+'\n','UTF-8'))
        self.ser.readline()  # Read in the line where Arduino echos trigger
        # Read in the line where Arduino prints the pulse width, and print it out once per iteration
        mess = str(self.ser.readline())
        if(printit):
            print (mess)
        for ic in range(0, self.nADC):
            line = int(self.ser.readline())
            if line >= 8192: # 8192 = 2^13, rollover bit?
                val = (line-16383)*1.22
            else:
                val = (line+1)*1.22 # where does this factor come from? it doesn't change frequency so not important
            if ic < self.nADC-1: # why is this needed?
                self.ADC[ic] = float(val)
        # center
        self.ADC = self.ADC-self.ADC.mean()

    def loop(self,npulses):
        print("Looping over",npulses,"pulses")
        # set initial pulse width according to 1/2 the breaking tensio
        pulse_width = 0.5*self.period(self.breaktension)
        ifreq = 0.5/pulse_width
        print(f"Initial frequency = {ifreq:.1f} Hz, pulse width = {pulse_width:.6f} seconds")
        for ik in range(0, npulses):
            self.PulseAndRead(pulse_width*1e6,ik==0) # microseconds
            freq = self.frequency()
            # convert to a tension
            tension = self.tension_gm(freq)
            print(f"Measured fundamental frequency {freq:.1f} Hz, corresponding to a tension of {tension:.1f} gm")
            # update the pulse width
            0.5*self.period(tension)


