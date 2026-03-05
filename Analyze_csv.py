# extract primary frequency from csv file

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
import csv

class Analyze_csv(object):
    def __init__(self,filename,firstrow,lastrow):
        nrows = lastrow-firstrow+1
        self.Times = [None]*nrows
        self.Volts = [None]*nrows

        with open(filename, 'r') as csvfile:
            reader = csv.DictReader(csvfile,dialect='unix',fieldnames=["dummy1","dummy2","dummy3","Seconds","Volts"])
            irow = 0
            jrow = 0
            for row in reader:
                if (irow >= firstrow) & (irow <= lastrow) :
#                    print(row['Seconds'], row['Volts'])
                    self.Times[jrow] = float(row['Seconds'])
                    self.Volts[jrow] = float(row['Volts'])
                    jrow += 1
                irow += 1

    def print(self,firstrow=0,lastrow=-1):
        if lastrow < 0:
            lastrow = len(self.Times)-1
        for irow in range(firstrow,lastrow):
            print (self.Times[irow],self.Volts[irow])

    def plot(self,firstrow=0,lastrow=-1):
        if lastrow < 0:
            lastrow = len(self.Times)-1
        fig, (timed,freqd) = plt.subplots(2,1,layout='constrained', figsize=(20,10))
        timeline = timed.plot(self.Times,self.Volts,scalex=True,scaley=True)
        timed.set_xlabel("Time (seconds)")
        timed.set_ylabel("Signal (Volts)")

        # compute the sampling frequency in KHz
        nsamp = len(self.Times)
        sfreq = nsamp/((self.Times[nsamp-1]-self.Times[0]))
        # Compute Fourier transform of windowed signal
        windowed = self.Volts * blackmanharris(nsamp)
        voltfft = fft(windowed)
        xf = fftfreq(nsamp,1.0/sfreq)[:nsamp//2]
        #print(windowed)
        nplot = 400
        freqplt =freqd.semilogy(xf[1:nplot//2], 2.0/nplot * np.abs(voltfft[1:nplot//2]), '-r')
        freqd.set_xlabel("Frequency (Hz)")
        freqd.set_ylabel("Amplitude")
    # Find the peak (primary harmonic) and interpolate around it to get a more accurate peak
        nmax = 400
        i = argmax(abs(voltfft[:nmax]))
        true_i = parabolic(log(abs(voltfft)), i)[0]

        # Convert to equivalent frequency
        # compute the sampling frequency in KHz
        ffreq = sfreq * true_i / len(windowed)
        print(f"Fundamental frequency = {ffreq:.2f} Hz")
        # now compute tension
        mu = 9.47e-6 # linear density of 25 micron diameter wire in kg/m
        g = 9.81 # gravitational constant
        length = 0.65 # wire length in meters
        tension = mu*np.square(ffreq*2*length) # tension in N
        wt = 1000*tension/g # equivalent tension in grams
        print(f"Wire tension = {wt:.2f} grams")
