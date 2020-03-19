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


class CorPlotMatScan(object):
    """Unpack a correlation plot scan .mat file"""
    def __init__(self, mat_file):
        try:
            data = sio.loadmat(mat_file)['data'][0][0]
        except Error as e:
            print('Error loading mat file: {0}'.format(e))
        self._file = mat_file
        self._fields = data.dtype.names
        self._accel = self._unpack_accl(data)
        self._statuses = self._unpack_statuses(data)
        self._ctrl_dict = self._unpack_ctrl_pv(data)
        self._read = self._unpack_read_pv(data)  # [pv][iteration][readings]
        self._twiss_pv = None  # Don't have file with this yet
        self._twiss_std = None  # Don't have file with this yet
        self._beam = self._unpack_beam(data)
        self._prof_pv = self._unpack_prof(data)
        self._ts = self._unpack_ts(data)
        #self._config = data[6]

    @property
    def file(self):
        """Loaded .mat file"""
        return self._file

    @property
    def control_dict(self):
        return self._ctrl_dict

    @property
    def accelerator(self):
        return self._accel

    def _unpack_accl(self, data):
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
        the appropriate key for the data (provided by dtype names)"""
        if BEAM not in self._fields:
            return None

        idx = self._fields.index(BEAM)
        beam = data[idx]
        names = beam.dtype.names
        beams = dict()
        for i, iteration in enumerate(beam):  # List of iterations
            beams[i] = [[dict(zip(names, fit)) for fit in sample] \
            for sample in iteration]

        return beams

    def _unpack_prof(self, data):
        if PROF not in self._fields:
            return None

        idx = self._fields.index(PROF)
        prof = data[idx]
        names = prof.dtype.names

        for pv in prof:
            
        return prof

    def _unpack_ts(self, data):
        """Unpack the timestamp, datetime.fromordinal not in current version"""
        if TS not in self._fields:
            return None

        idx = self._fields.index(TS)
        ts = data[idx][0][0]
        return ts
            
# from cor_plot_mat_scan import CorPlotMatScan as C
# data = C('test_scan.mat')           
        
        
