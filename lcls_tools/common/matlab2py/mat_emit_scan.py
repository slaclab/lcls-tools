import scipy.io as sio
import os

VAL = "val"
UNITS = "egu"

FIT = [
    "Gaussian",
    "Asymmetric",
    "Super",
    "RMS",
    "RMS cut peak",
    "RMS cut area",
    "RMS floor",
]

STAT = "status"
SCAN_TYPE = "type"
NAME = "name"
QUAD_NAME = "quadName"
QUAD_VALS = "quadVal"
USE = "use"
TS = "ts"
BEAM = "beam"
BEAM_STD = "beamStd"
BEAM_LIST = "beamList"
Q_LIST = "chargeList"
Q = "charge"
Q_STD = "chargeStd"
R_MAT = "rMatrix"
TWISS_0 = "twiss0"
ENERGY = "energy"
TWISS = "twiss"
TWISS_STD = "twissstd"
ORBIT = "orbit"
ORBIT_STD = "orbitstd"
TWISS_PV = "twissPV"

# Disclaimer:  It is up to user to verify what they are getting makes
# sense in the context of thes scan types


class MatEmitScan(object):
    def __init__(self, mat_file):
        if not os.path.isfile(mat_file):
            raise FileNotFoundError(
                f"Could not find {mat_file}, please provide a valid emittance matlab file."
            )
        try:
            data = sio.loadmat(mat_file)["data"][0][0]
            self._fields = data.dtype.names
            self._file = mat_file
            self._status = self._unpack_prop(STAT, data)
            self._scan_type = self._unpack_prop(SCAN_TYPE, data)
            self._name = self._unpack_prop(NAME, data)
            self._quad_name = self._unpack_prop(QUAD_NAME, data)
            self._quad_vals = self._unpack_prop(QUAD_VALS, data)
            self._use = self._unpack_prop(USE, data)
            self._ts = self._unpack_prop(TS, data)
            self._beam = self._unpack_beam(data)  # data[7][iteration][fit][names]
            self._charge = self._unpack_prop(Q, data)
            self._charge_std = self._unpack_prop(Q_STD, data)
            self._r_matrix = self._unpack_prop(
                R_MAT, data
            )  # List of r matrix per iteration
            self._twiss_0 = self._unpack_prop(
                TWISS_0, data
            )  # data[14]  # No clue how these fields are arranged
            self._energy = self._unpack_prop(ENERGY, data)
            self._twiss = self._unpack_prop(TWISS, data)
            self._twiss_std = self._unpack_prop(TWISS_STD, data)
            self._orbit = self._unpack_prop(ORBIT, data)
            self._orbit_std = self._unpack_prop(ORBIT_STD, data)
            self._twiss_pv = self._unpack_twiss_pv(data)
        except Exception as e:
            print("Error loading mat file: {0}".format(e))

    @property
    def fields(self):
        """The names of meta data fields associated with scan"""
        return self._fields

    @property
    def mat_file(self):
        """Mat file loaded"""
        return self._file

    @property
    def status(self):
        """Array of 0 or 1, no idea what status it's looking at"""
        if self._status is not None:
            return [status[0] for status in self._status]

    @property
    def scan_type(self):
        """Type of scan, useful with names like 'scan', lol"""
        if self._scan_type:
            return str(self._scan_type[0])

    @property
    def name(self):
        """Name of profile monitor/WS used for measurement"""
        if self._name:
            return str(self._name[0][0][0])

    @property
    def quad_name(self):
        """Magnet scanned for emit measurement"""
        if self._quad_name:
            return str(self._quad_name[0])

    @property
    def quad_vals(self):
        """Values of magnet B field used in scan"""
        if self._quad_vals is not None:
            return self._quad_vals[0]

    @property
    def iterations(self):
        """Iterations of quad scan"""
        if self._quad_vals is not None:
            return len(self._quad_vals[0])

    @property
    def use(self):
        """Array of 1 or 0, 1 means used in calculations"""
        if self._use is not None:
            return [use[0] for use in self._use]

    @property
    def timestamp(self):
        """Matlab timestamp convention, use datetime.fromordinal"""
        if self._ts:
            return self._ts[0][0]

    @property
    def beam(self):
        """list of dictionaries each iteration's stats, this needs more
        properties or helper functions to parse to user's needs"""
        return self._beam

    @property
    def charge(self):
        """Charge measured during each scan iteration, good for normalizing"""
        if self._charge:
            return self._charge[0][0]

    @property
    def charge_std(self):
        """STD of charge during each iteration, good for dropping noisy points"""
        if self._charge_std:
            return self._charge_std[0][0]

    @property
    def rmat(self):
        """list of r matrix, one per iteration"""
        if self._r_matrix is not None:
            return self._r_matrix[0]

    @property
    def twiss_0(self):
        """Your guess is as good as mine, maybe initial twiss"""
        return self._twiss_0

    @property
    def energy(self):
        """Energy of beam at measurement location, pretty sure it's GeV"""
        if self._energy:
            return self._energy[0][0]

    @property
    def twiss(self):
        """Twiss parameters at end of scan for each type of fit, more
        useful properties and unpacking below"""
        return self._twiss

    @property
    def twiss_std(self):
        """STD of twiss calculations, did not offer more props on this"""
        return self._twiss_std

    @property
    def orbit(self):
        """No bpm names to indicate measurement locations"""
        return self._orbit

    @property
    def orbit_std(self):
        """STD of orbit measurements"""
        return self._orbit_std

    @property
    def emit_x(self):
        """Return dict of emit x vals with fit as key"""
        if self._twiss_pv:
            return dict(zip(FIT, self._twiss_pv[0][VAL]))

    @property
    def beta_x(self):
        """Return dict of beta x vals with fit as key"""
        if self._twiss_pv:
            return dict(zip(FIT, self._twiss_pv[1][VAL]))

    @property
    def alpha_x(self):
        """Return dict of alpha x vals with fit as key"""
        if self._twiss_pv:
            return dict(zip(FIT, self._twiss_pv[2][VAL]))

    @property
    def bmag_x(self):
        """Return dict of match x vals with fit as key"""
        if self._twiss_pv:
            return dict(zip(FIT, self._twiss_pv[3][VAL]))

    @property
    def emit_y(self):
        """Return dict of emit y vals with fit as key"""
        if self._twiss_pv:
            return dict(zip(FIT, self._twiss_pv[4][VAL]))

    @property
    def beta_y(self):
        """Return dict of beta y vals with fit as key"""
        if self._twiss_pv:
            return dict(zip(FIT, self._twiss_pv[5][VAL]))

    @property
    def alpha_y(self):
        """Return dict of alpha y vals with fit as key"""
        if self._twiss_pv:
            return dict(zip(FIT, self._twiss_pv[6][VAL]))

    @property
    def bmag_y(self):
        """Return dict of match y vals with fit as key"""
        if self._twiss_pv:
            return dict(zip(FIT, self._twiss_pv[7][VAL]))

    ########## Helper Functions ###########

    def _unpack_prop(self, prop, data):
        """General way to pull out specific values for the fields present in data"""
        if prop not in self._fields:
            return None

        idx = self._fields.index(prop)
        return data[idx]

    def _unpack_beam(self, data):
        """Unpacks to a list of lists.  Each list is an iteration which contains
        all the data for each fit.  Each fit is a dictionary with all the associated types of data.
        Also, since beam_std is a duplicate of beam except for stats, they are added to the
        dictionary"""
        if BEAM not in self._fields:
            return None

        idx_beam = self._fields.index(BEAM)
        beam = data[idx_beam]

        beam_std = None
        if BEAM_STD in self._fields:
            idx_beam_std = self._fields.index(BEAM_STD)
            beam_std = data[idx_beam_std]

        names = beam.dtype.names
        temp = []
        # Go through each scan iteration
        for i1, iteration in enumerate(beam):
            fit_list = []
            # Go through each fit method
            for i2, fit in enumerate(iteration):
                iter_fit = dict()
                # Go through metadata provided
                for i3, name in enumerate(names):
                    iter_fit[name] = fit[i3]
                # Throw stats in there
                if beam_std is not None:
                    iter_fit["stats_std"] = beam_std[i1][i2][10]
                else:
                    iter_fit["stats_std"] = []
                fit_list.append(iter_fit)
            temp.append(fit_list)

        return temp

    def _unpack_twiss_pv(self, data):
        """All the twiss parameters from the emittance scan.
        7 vals corresponding to each fit method"""
        if TWISS_PV not in self._fields:
            return None

        idx_twiss_pv = self._fields.index(TWISS_PV)
        twiss_pv = data[idx_twiss_pv]

        names = twiss_pv.dtype.names
        temp1 = []
        for val in twiss_pv:
            temp2 = dict()
            for i, name in enumerate(names):
                if name != UNITS:
                    if isinstance(val[0][i][0], bytes):
                        temp2[name] = str(val[0][i][0].decode("utf-8"))
                    else:
                        temp2[name] = val[0][i][0]
            temp1.append(temp2)

        return temp1
