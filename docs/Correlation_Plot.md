# Correlation Plot
These tools are used to find a relationship between the size of the beam and the magnet strength. The sections below contain packages that are used to view and analyze the correlation plots as well as test if that code works correctly. 

# How to view a Correlation Plot
The tool currently has hard coded paths specific to the author of the code and will need to be updated to suit everyone. This package can be installed from {GitHub}:('https://github.com/slaclab/lcls-tools/tree/master/lcls_tools/cor_plot')  

### Useful Information
 * Uses cor_plot tools from lcls-tools.
 * Loads data and plots a correlation plot from the data.
 * Error bars indicate the deviance from the mean at each x value.
 * x values (magnet strength) are found using the tool ctrl_vals.
 * At each x value, some number of iterations will be taken. 

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
# Correlation Plot Analysis
This utility can take a cor plot .mat file and turn it into a python data object.  The goal is to present the data from a cor plot in a meaningful way. This utility has a couple of test files that are used for testing, but we can use them for examples.  All examples are run from this directory.  Current example is using Python2.7

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

Package to analize data:
```sh
import scipy.io as sio
import numpy as np

FIT = [
    'Gaussian',
    'Asymmetric',
    'Super',
    'RMS',
    'RMS cut peak',
    'RMS cut area',
    'RMS floor'
]

ACCL = 'accelerator'
STAT = 'status'
CTRL = 'ctrlPV'
READ = 'readPV'
BEAM = 'beam'
PROF = 'profPV'
TS = 'ts'
CONFIG = 'config'

# Disclaimer:  It is up to user to verify what they are getting makes
# sense in the context of thes scan types

class CorPlotMatScan(object):
    """Unpack a correlation plot scan .mat file"""
    def __init__(self, mat_file):
        try:
            data = sio.loadmat(mat_file)['data'][0][0]
            self._file = mat_file
            self._fields = data.dtype.names
            self._accel = self._unpack_accl(data)
            self._statuses = self._unpack_statuses(data)
            self._ctrl_dict = self._unpack_ctrl_pv(data)
            self._read = self._unpack_read_pv(data)  # [pv][iteration][readings]
            self._twiss_pv = None  # Don't have file with this yet
            self._twiss_std = None  # Don't have file with this yet
            self._beam, self._beam_names = self._unpack_beam(data)
            self._prof_pv = self._unpack_prof(data)
            self._ts = self._unpack_ts(data)
            self._config = self._unpack_config(data)
        except Exception as e:
            print('Error loading mat file: {0}'.format(e))

    @property
    def file(self):
        """Loaded .mat file"""
        return self._file

    @property
    def fields(self):
        """Data fields (keys) Henrik felt like populating for given scan, depends
        on what boxes are checked for measurements, so we'll never know unless
        we introspect because schema is not a thing in Henrik's code.  I've never
        seen code so uninterested in organizing data in an appreciable way...
        probably for job security?"""
        return self._fields

    @property
    def control_dict(self):
        """Ctrl PV and vals, units etc..."""
        return self._ctrl_dict

    @property
    def accelerator(self):
        """Accelerator name"""
        return self._accel

    @property
    def ctrl_pv(self):
        """PV being scanned, might need to change for 2D scans"""
        if self._ctrl_dict is not None:
            return self._ctrl_dict[0]['name']

        return None

    @property
    def iterations(self):
        """iterations for cor plot"""
        if self._ctrl_dict is not None:
            return len(self._ctrl_dict[0]['vals'])

        return 0

    @property
    def ctrl_vals(self):
        """Vals for ctrl pv in scan"""
        if self._ctrl_dict is not None:
            return self._ctrl_dict[0]['vals']

        return None

    @property
    def beam(self):
        """This is a huge amount of data"""
        return self._beam

    @property
    def beam_names(self):
        """The different keys for a beam dict for each iteration and fit"""
        return self._beam_names

    @property
    def timestamp(self):
        """Matlab timestamp (ordinal)"""
        return self._ts

    @property
    def config(self):
        """Random collection of data already available from above properties, lame"""
        return self._config

    @property
    def samples(self):
        if self._beam:
            return len(self._beam[0])

    def _unpack_accl(self, data):
        """Accelerator name such as LCLS, LCLS2, etc..."""
        # Need to write generic decorator for this behavior
        if ACCL not in self._fields:
            return None

        idx = self._fields.index(ACCL)
        return str(data[idx][0])

    def _unpack_statuses(self, data):
        """Pull statuses out of the nested array"""
        if STAT not in self._fields:
            return None

        idx = self._fields.index(STAT)
        statuses = data[idx]
        return [status[0] for status in statuses]

    def _unpack_ctrl_pv(self, data):
        """Produces a list of ctrl pv dicts with list of vals and 
        tmestamps.
        """
        if CTRL not in self._fields:
            return None

        idx = self._fields.index(CTRL)
        ctrls = data[idx]
        ctrl_list = []
        for ctrl in ctrls:
            temp = dict()
            temp['name'] = str(ctrl[0][0][0])
            temp['desc'] = str(ctrl[0][3][0])
            temp['egu'] = str(ctrl[0][4][0])
            temp['vals'] = [point[1][0][0] for point in ctrl]
            temp['times'] = [point[2][0][0] for point in ctrl]
        
            ctrl_list.append(temp)

        return ctrl_list
        
    def _unpack_read_pv(self, data):
        """Create a list of dictionaries for all the readback pvs
        Each val and time key is a 2 d array for each data point as each point
        has a number of readings"""
        if READ not in self._fields:
            return None

        idx = self._fields.index(READ)
        pvs = data[idx]
        read = []
        for pv in pvs:  # FML
            temp = dict()
            temp['name'] = str(pv[0][0][0][0])
            temp['desc'] = str(pv[0][0][3][0])
            temp['egu'] = str(pv[0][0][4][0])
            temp['vals'] = [[i[1][0][0] for i in point] for point in pv]
            temp['times'] = [[i[2][0][0] for i in point] for point in pv]
                
            read.append(temp)

        return read

    def _unpack_beam(self, data):
        """Unpack beam, returns dict with iteration number as key.  
        The value is a list of samples, each sample being a dict with
        the appropriate key for the data (provided by dtype names).  I'm leaving
        the business logic of extracting these to @property calls"""
        if BEAM not in self._fields:
            return None, None

        idx = self._fields.index(BEAM)
        beam = data[idx]
        names = beam.dtype.names
        beams = dict()
        for i, iteration in enumerate(beam):  # List of iterations
            beams[i] = [[dict(zip(names, fit)) for fit in sample] \
            for sample in iteration]

        return beams, names

    def _unpack_prof(self, data):
        """Unpack profile monitor pvs and data.  Not super clean
        reformatting, but it's just a list of PV data lists.  The PV
        data list contains a list of iterations, each iteration contains
        samples"""
        if PROF not in self._fields:
            return None

        idx = self._fields.index(PROF)
        prof = data[idx]
        names = prof.dtype.names
        prof_pvs = dict()
        for pv in prof:
            if isinstance(pv[0][0][0], unicode):  # one sample
                prof_pvs[str(pv[0][0][0])] = pv
            else:  # Multiple samples
                prof_pvs[str(pv[0][0][0][0])] = pv  

        return prof_pvs

    def _unpack_ts(self, data):
        """Unpack the timestamp, datetime.fromordinal not in current version"""
        if TS not in self._fields:
            return None

        idx = self._fields.index(TS)
        ts = data[idx][0][0]
        
        return ts

    def _unpack_config(self, data):
        """As far as I can tell this is not useful except for ctrl pv,
        but we get that with control dict"""
        if CONFIG not in self._fields:
            return None

        idx = self._fields.index(CONFIG)
        config = data[idx]

        return config

# from cor_plot_mat_scan import CorPlotMatScan as C
# data = C('test_scan.mat')           
```

#Test for Analysis
Tests if the functions in the analysis are performing properly

```sh
import sys
import unittest
import numpy as np
from cor_plot_mat_scan import CorPlotMatScan as CPMS

# We need a scan where all struct names are populated
# to fully test.  Would have been nice to populate every
# possible field with something (even empty array), but that
# would be too similar to something that makes sense in the world
# of data structures

BAD_FILE = 'test_scan.mat'

# TEST FIle metadata
BEAM_NAMES_TEST = (
    'profx',
    'xStat',
    'xStatStd',
    'profy',
    'yStat',
    'yStatStd',
    'profu',
    'uStat',
    'uStatStd',
    'method',
    'stats',
    'statsStd'
)
TEST_FILE = 'test_scan2.mat'
FIELDS_TEST = (
    'accelerator',
    'status',
    'ctrlPV',
    'readPV',
    'beam',
    'profPV',
    'ts',
    'config'
)
ACCL_TEST = 'LCLS2'
CTRL_PV_TEST = 'MIRR:LGUN:820:M3_MOTR_H'
CTRL_VAL_0_TEST = 0.85  # First value of scan ctrl pv
ITER_TEST = 27
TS_TEST = 737730.05
SAMPLES_TEST = 2

#QE File metadata
BEAM_NAMES_QE = None
QE_FILE = 'qe_scan.mat'
FIELDS_QE = (
    'accelerator',
    'status',
    'ctrlPV',
    'readPV',
    'beam',
    'profPV',
    'ts',
    'config'
)
ACCL_QE = 'LCLS2'
CTRL_PV_QE = 'MIRR:LGUN:820:M3_MOTR_H'
CTRL_VAL_0_QE = 1.93
ITER_QE = 400
TS_QE = 737728.26

class CorPlotMatScanTest(unittest.TestCase):

    def test_init_mat_file_test(self):
        cpms = CPMS(TEST_FILE)
        self.assertEqual(cpms.fields, FIELDS_TEST)
        self.assertEqual(cpms.accelerator, ACCL_TEST)
        self.assertEqual(cpms.ctrl_pv, CTRL_PV_TEST)
        self.assertEqual(cpms.iterations, ITER_TEST)
        self.assertEqual(round(cpms.ctrl_vals[0], 3), CTRL_VAL_0_TEST)
        self.assertEqual(cpms.beam_names, BEAM_NAMES_TEST)
        self.assertEqual(round(cpms.timestamp, 2), TS_TEST)
        self.assertEqual(cpms.samples, SAMPLES_TEST)

    def test_init_mat_file_qe(self):
        cpms = CPMS(QE_FILE)
        self.assertEqual(cpms.fields, FIELDS_QE)
        self.assertEqual(cpms.accelerator, ACCL_QE)
        self.assertEqual(cpms.ctrl_pv, CTRL_PV_QE)
        self.assertEqual(cpms.iterations, ITER_QE)
        self.assertEqual(round(cpms.ctrl_vals[0],2), CTRL_VAL_0_QE)
        self.assertEqual(cpms.beam_names, None)
        self.assertEqual(round(cpms.timestamp, 2), TS_QE)

    def test_init_bad_file(self):
        self.assertRaises(Exception, CPMS(BAD_FILE))

if __name__ == '__main__':
    unittest.main()
```
