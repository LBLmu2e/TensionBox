# extract primary frequency from csv file

import sys
import numpy as np
from numpy.fft import rfft, irfft
from numpy import argmax, sqrt, mean, diff, log
import matplotlib
import matplotlib.pyplot as plt
import math, time, os
import scipy
from scipy.signal import fftconvolve
from scipy.signal.windows import blackmanharris
from parabolic import parabolic
import csv


def freq_from_fft(signal, fs):
    """ Estimate frequency from peak of FFT """

    # Compute Fourier transform of windowed signal
    windowed = signal * blackmanharris(len(signal))
    f = rfft(windowed)
    print(windowed)
    print("f",f)

    # Find the peak and interpolate to get a more accurate peak
    i = argmax(abs(f[:nmax]))  # Just use this for less-accurate, naive version
    true_i = parabolic(log(abs(f)), i)[0]

    # Convert to equivalent frequency
    return fs * true_i / len(windowed)


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
                    self.Times[jrow] = row['Seconds']
                    self.Volts[jrow] = row['Volts']
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


