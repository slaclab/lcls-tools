# Correlation Plots
These tools are used to find a relationship between the size of the beam and the    magnate strength. The sections below contains packages that are used to view and analyze the correlation plots as well as test if that code works correctly. 


# How to view a Correlation Plot
The python code below unpacks a mat file and allows us to examine the correlation plot. The tool currently has hard coded paths specific to the author of the code and will need to be updated to suit everyone.  

### Useful Information
 -Uses cor_plot tools from lcls-tools.
 -Loads data and plots a correlation plot from the data.
 -Error bars indicate the deviance from the mean at each x value.
 -x values (magnet strength) are found using the tool ctrl_vals.
 -At each x value, some number of iterations will be taken. 

A specific fit and beam name can be chosen from the following lists:
FIT = ['Gaussian', 'Asymmetric', 'Super', 'RMS', 'RMS cut peak', 'RMS cut area', 'RMS floor']
beam_names: profx, xStat, profy, yStat, profu, uStat, stats

In each iteration, some number of samples are taken.
The mean of the samples in each iteration is taken and appended to a new array.
This new array is used for the y values (beam size).
The x array is plotted against the y array, along with error bars.

```sh
import sys
import matplotlib.pyplot as plt
import numpy as np

sys.path.append('C:/Users/asihn/Anaconda3/Lib/site-packages')
sys.path.append('C:/Users/asihn/Desktop/SLAC/lcls-tools/')
sys.path.append('C:/Users/asihn/Desktop/SLAC/lcls-tools/lcls_tools/devices/profile_monitor')
sys.path.append('C:/Users/asihn/Desktop/SLAC/lcls-tools/lcls_tools/devices/magnet')
sys.path.append('C:/Users/asihn/Desktop/SLAC/lcls-tools/lcls_tools/image_processing')
sys.path.append('C:/Users/asihn/Desktop/SLAC/lcls-tools/lcls_tools/cor_plot')

from cor_plot_mat_scan import CorPlotMatScan as C

# load data
data = C("C:/Users/asihn/Desktop/SLAC/emittance_gui/CorrelationPlot/CorrelationPlot-SOLN_IN20_121_BCTRL-2020-06-21-091733.mat")

# set the number of samples
s = data.samples

# can use to see the number of data points
print(data.beam.keys())

# set the x values for plot
x = data.ctrl_vals

# format: data.beam[iteration][sample][fit][beam_name]
# iteration: length of x
# sample: number of samples
# fit: index 0-6 (see types of fit below)
# beam_name": string chosen from types of beam_names below
# types of fit: ['Gaussian', 'Asymmetric', 'Super', 'RMS', 'RMS cut peak', 'RMS cut area', 'RMS floor']
# types of beam_name: profx, xStat, profy, yStat, profu, uStat, stats

yarray = []
yerr = []

for i in range(0, len(x)):

    yvals = []

    for j in range(0, s):
        # store data in array
        yvals.append(((data.beam[i][j][0]['xStat'])[0])[2])

    # calculate average of data and store in array
    meany = np.mean(yvals)
    yarray.append(meany)

    # calculate error of data and store in array
    stdy = np.std(yvals)
    yerr.append(stdy)

# Correlation plot
plt.xlabel('Magnet Strength', fontsize=20)
plt.ylabel('X rms (beam size)', fontsize=20)
plt.errorbar(x, yarray, yerr=yerr, label='xStat', ecolor='red', elinewidth=4, linewidth=2, marker='o', markersize=4)
plt.title('Correlation Plot', fontsize=30)
plt.legend(loc='upper left')

plt.show()
```

