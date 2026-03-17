#
# class to make rolling wire tension measurements
#
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from collections import deque

class RollingTension(object):
    def __init__(self,wirelen=0.65,pltsamp=50,maxsamp=100000): # wire length in m
        self.wirelen = wirelen
        self.pltsamp = pltsamp
        self.maxsamp = maxsamp
        self.tension = deque(maxlen=pltsamp) # Keeps last 50 points
        self.nsamp = 0 # count the number of samples made
        self.fscale = 3.864e-3 * wirelen*wirelen # scale
        self.fig, self.ax = plt.subplots()
        self.line, = self.ax.plot([], [], 'ro')

    def tension_gm(self,freq):
        # compute the tension in gm equivalent given the frequency in Hz
        return self._fscale*freq*freq

    def period(self,tension_gm): # return period in seconds for a given tension in gm
        return self.wirelen*np.sqrt(self.fscale/tension_gm)


    def addSample(self,tension):
        if(self.nsamp >= self.pltsamp)):
            self.tension.popleft()
        self.tension.append(tension)
        self.nsamp += 1
        self.line.set_ydata(self.tension)
        self.line.set_xdata(range(max(1,self.nsamp-self.pltsamp),self.nsamp))
        self.ax.relim()
        self.ax.autoscale_view()

# 4. Animate
    ani = animation.FuncAnimation(fig, update, interval=100)
    plt.show()


