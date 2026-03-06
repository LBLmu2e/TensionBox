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
import serial     ## from pyserial
import math, time, os

from datetime import datetime as dt

class LoopTension(object):
    def __init__(self,wirelen=0.65,npulses=1): # wire length in m
        self.wirelen = wirelen
        self.fscale = 3.864e-3 * wirelen*wirelen # scale between frequency and wire length
        self.nomtension = 80 # nominal tension
        self.maxtension = 100 # maximum tension when conditioning the wire
        self breaktension = 120 # breaking point!
        self.ArduinoPeriod = 1./8900. # effective period
        self.nplot = 200
        self.nmax = 400
        self.nADC = 2000          # Should match DataLength in the Arduino code
        self.ADC = [None]*self.nADC
        self.npulses = npulses
        # Find the arduino
        ports = [p.device for p in serial.tools.list_ports.comports()
             if 'VID:PID=2341:003D' in p.hwid]
        if len(ports)<1:
            print('Arduino not found \nPlug wire tensioner into any USB port')
            time.sleep(2)
            print("Exiting script")
            sys.exit()
        print("Arduino Due at {}".format(ports[0]))
        self.portloc ctr = ports[0]
        self.ser = serial.Serial(port=self.portloc, baudrate=115200)
        time.sleep(1)
        print("initialized\n")

    def tension_gm(self,freq):
        # compute the tension in gm equivalent given the frequency in Hz
        return self._fscale*freq*freq

    def period(self,tension_gm): # return period in seconds for a given tension in gm
        return self.wirelen*np.sqrt(self.fscale/tension_gm)

    def plot(self,start,stop):
        fig, (timed,freqd) = plt.subplots(2,1,layout='constrained', figsize=(20,10))
        tstep = stop-start
        timeline = timed.plot(range(start,stop,(stop-start)/len(self.ADC)),self.ADC,scalex=True,scaley=True)
        timed.set_xlabel("Time (seconds)")
        timed.set_ylabel("Signal (ADC)")

    def frequency(self):
        # compute the sampling frequency in KHz
        nsamp = len(self.ADC)
        windowed = self.ADC * blackmanharris(nsamp)
        voltfft = fft(windowed)
        xf = fftfreq(nsamp,self.ArduinoPeriod)[:nsamp//2]
        #print(windowed)
        nplot = 400
        freqplt =freqd.semilogy(xf[1:nplot//2], 2.0/nplot * np.abs(voltfft[1:nplot//2]), '-r')
        freqd.set_xlabel("Frequency (Hz)")
        freqd.set_ylabel("Amplitude")
    # Find the peak (primary harmonic) and interpolate around it to get a more accurate peak
        nmax = 400
        i = argmax(abs(voltfft[:nmax]))
        true_i = parabolic(log(abs(voltfft)), i)[0]
        # compute the sampling frequency in Hz
        ffreq = sfreq * true_i / len(windowed)
        return ffreq

    def PulseAndRead(self, pulse_width):
        # Trigger the Arduino to take data
        self.ser.write(b'5\n')
        # Write the desired pulse width
        self.ser.write(bytes(str(int(pulse_width))+'\n','UTF-8'))
        self.ser.readline()  # Read in the line where Arduino echos trigger

         # Read in the line where Arduino prints the pulse width, and print it out once per iteration
        print (str(self.ser.readline()))  # Read in and print line where Arduino prints pulse width
        print(self.ser.readline().decode("utf-8").strip() )
        print(int(pulse_width))
        for ic in range(0, self.nADC):
            line = int(self.ser.readline())
            if line >= 8192:
                val = (line-16383)*1.22
            else:
                val = (line+1)*1.22

            self.ADC[ic] = val

    def loop(self):
        print("Looping over",self.npulses," pulses")A
        # set initial pulse width according to 1/2 the breaking tensio
        pulse_width = 0.5*self.period(self.breaktension)
        for ik in range(0, self.npulses):
            self.PulseAndRead(pulse_width)
            freq = self.frequency()
            # convert to a tension
            tension = self.tension(freq)
            print("Measured fundamental frequency",freq,"Hz, corresponding to a tension of",tension,"gm")
            # update the pulse width
            0.5*self.period(tension)

