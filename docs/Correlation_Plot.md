# Correlation Plots
These tools are used to find a relationship between the size of the beam and the    magnate strength. The sections below contains packages that are used to view and analyze the correlation plots as well as test if that code works correctly. 


# How to view a Correlation Plot
The purpose of this package is to unpack a mat file and allow the examination of the correlation plots. The tool currently has hard coded paths specific to the author of the code and will need to be updated to suit everyone. You can find this package on [GitHub.com](https://github.com/slaclab/lcls-tools/tree/master/lcls_tools/cor_plot). 

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

# Correlation Plot Analysis
This utility, found [here](https://github.com/slaclab/lcls-tools/blob/python3devel/lcls_tools/cor_plot/cor_plot_mat_scan.py), can take a cor plot .mat file and turn it into a python data object.  The goal is to present the data from a cor plot in a meaningful way. Below shows an example of the test that was used for theoriginal package. The full test can be found [here](https://github.com/slaclab/lcls-tools/blob/python3devel/lcls_tools/cor_plot/cor_plot_mat_scan_test.py).

Example: 'test_scan.mat'

Import and Initialize cor plot data object
 ```
>>> from cor_plot_mat_scan import CorPlotMatScan as CPMS
>>> cpms = CPMS('test_scan.mat')
```

Access Properties.  Here are some of the properties that are defined for the data object.
```
>>> cpms.fields
('accelerator', 'status', 'ctrlPV', 'beam', 'profPV', 'ts', 'config')
>>> cpms.accelerator
'LCLS2'
>>> cpms.ctrl_pv
'SOLN:GUNB:212:BCTRL'
>>> cpms.iterations
10
>>> cpms.ctrl_vals
[0.072999999999999995, 0.073888888888888879, 0.074777777777777776, 0.07566666666666666, 0.076555555555555557, 0.077444444444444441, 0.078333333333333338, 0.079222222222222222, 0.080111111111111119, 0.081000000000000003]
>>> cpms.beam_names
('profx', 'xStat', 'xStatStd', 'profy', 'yStat', 'yStatStd', 'profu', 'uStat', 'uStatStd', 'method', 'stats', 'statsStd')
>>> cpms.timestamp
737730.05017097027
>>> cpms.samples
2
```

Access Beam Data.  This is very tricky and could use some cleanup.  This is all the metadata associated with the scan and goes by the nature of cpms.beam[iteration][sample][fit].  The fits are in the following order FIT = ['Gaussian', 'Asymmetric', 'Super', 'RMS', 'RMS cut peak', 'RMS cut area', 'RMS floor'].

Example, say I want to get a specific field from beam_names.  Say 'profx' for iteration 3, sample 2 and 'RMS cut peak' (5, index of 4):
```
>>> cpms.beam[2][1][4]['profx']
array([[ -8.04000000e+03,  -8.02392000e+03,  -8.00784000e+03, ...,
          5.37072000e+03,   5.38680000e+03,   5.40288000e+03],
       [  0.00000000e+00,   0.00000000e+00,   2.49000000e+02, ...,
          1.72000000e+02,   0.00000000e+00,   2.64000000e+02],
       [  1.72791308e+01,   1.77236486e+01,   1.81784282e+01, ...,
          4.98085984e+00,   4.84116133e+00,   4.70507716e+00]])
```

As you can see, this whole beam property needs a lot of cleanup.  I do not even know what profx is, maybe an x projection/histogram of the profile monitor?  Your guess is as good as mine.  Good luck!