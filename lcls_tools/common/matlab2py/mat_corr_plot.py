import os
import scipy.io as sio

FIT = [
    "Gaussian",
    "Asymmetric",
    "Super",
    "RMS",
    "RMS cut peak",
    "RMS cut area",
    "RMS floor",
]

ACCL = "accelerator"
STAT = "status"
CTRL = "ctrlPV"
READ = "readPV"
BEAM = "beam"
PROF = "profPV"
TS = "ts"
CONFIG = "config"

# Disclaimer:  It is up to user to verify what they are getting makes
# sense in the context of thes scan types


class MatCorrPlot(object):
    """Unpack a correlation plot scan .mat file"""

    def __init__(self, mat_file):
        if not os.path.isfile(mat_file):
            raise FileNotFoundError(
                f"Could not find {mat_file}, please provide a valid correlation matlab file."
            )
        try:
            data = sio.loadmat(mat_file)["data"][0][0]
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
            print("Error loading mat file: {0}".format(e))

    @property
    def file(self):
        """Loaded .mat file"""
        return self._file

    @property
    def fields(self):
        """Data fields (keys) populated for given scan, depends
        on what boxes are checked for measurements"""
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
            return self._ctrl_dict[0]["name"]

        return None

    @property
    def iterations(self):
        """iterations for cor plot"""
        if self._ctrl_dict is not None:
            return len(self._ctrl_dict[0]["vals"])

        return 0

    @property
    def ctrl_vals(self):
        """Vals for ctrl pv in scan"""
        if self._ctrl_dict is not None:
            return self._ctrl_dict[0]["vals"]

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
        """Collection of measurment properties"""
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
            temp["name"] = str(ctrl[0][0][0])
            temp["desc"] = str(ctrl[0][3][0])
            temp["egu"] = str(ctrl[0][4][0])
            temp["vals"] = [point[1][0][0] for point in ctrl]
            temp["times"] = [point[2][0][0] for point in ctrl]

            ctrl_list.append(temp)

        return ctrl_list

    def _unpack_read_pv(self, data):
        """Create a list of dictionaries for all the readback pvs.
        Each val and time key is a 2d array for each data point as each point
        has a number of readings"""
        if READ not in self._fields:
            return None

        idx = self._fields.index(READ)
        pvs = data[idx]
        read = []
        for pv in pvs:  # FML
            temp = dict()
            temp["name"] = str(pv[0][0][0][0])
            temp["desc"] = str(pv[0][0][3][0])
            temp["egu"] = str(pv[0][0][4][0])
            temp["vals"] = [[i[1][0][0] for i in point] for point in pv]
            temp["times"] = [[i[2][0][0] for i in point] for point in pv]

            read.append(temp)

        return read

    def _unpack_beam(self, data):
        """Unpack beam, returns dict with iteration number as key.
        The value is a list of samples, each sample being a dict with
        the appropriate key for the data (provided by dtype names).
        The business logic of extracting these is in @property calls"""
        if BEAM not in self._fields:
            return None, None

        idx = self._fields.index(BEAM)
        beam = data[idx]
        names = beam.dtype.names
        beams = dict()
        for i, iteration in enumerate(beam):  # List of iterations
            beams[i] = [
                [dict(zip(names, fit)) for fit in sample] for sample in iteration
            ]

        return beams, names

    def _unpack_prof(self, data):
        """Unpack profile monitor pvs and data. A list of PV data.  The PV
        data list contains a list of iterations, each iteration contains
        samples"""
        if PROF not in self._fields:
            return None

        idx = self._fields.index(PROF)
        prof = data[idx]
        prof_pvs = dict()
        for pv in prof:
            if isinstance(pv[0][0][0], bytes):  # one sample
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
        """Config data, some of which is in the control dict"""
        if CONFIG not in self._fields:
            return None

        idx = self._fields.index(CONFIG)
        config = data[idx]

        return config
