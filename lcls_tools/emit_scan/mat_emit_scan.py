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

STAT = 'status'
TYPE = 'type'
NAME = 'name'
QUAD_NAME = 'quadName'
QUAD_VAL = 'quadVal'
USE = 'use'
TS = 'ts'
BEAM = 'beam'
BEAM_STD = 'beamStd'
BEAM_LIST = 'beamList'
Q_LIST = 'chargeList'
Q = 'charge'
Q_STD = 'chargeStd'
R_MAT = 'rMatrix'
TWISS_0 = 'twiss0'
ENERGY = 'energy'
TWISS = 'twiss'
TWISS_STD = 'twissstd'
ORBIT = 'orbit'
ORBIT_STD = 'orbitstd'
TWISS_PV = 'twissPV'

# This could use some code duplication love once it's figured out

class MatEmitScan(object):
    def __init__(self, mat_file):
        try:
            data = sio.loadmat(mat_file)['data'][0][0]
            self._fields = data.dtype.names
            self._file = mat_file
            self._status = [status[0] for status in data[0]]
            self._type = str(self._unpack_prop(TYPE, data)[0])
            self._name = str(self._unpack_prop(NAME, data)[0][0][0])
            self._quad_name = str(self._unpack_prop(QUAD_NAME, data)[0])
            self._quad_val = self._unpack_prop(QUAD_VAL, data)[0]
            self._use = [use[0] for use in data[5]]
            self._ts = self._unpack_prop(TS, data)[0][0]
            self._beam = self._unpack_beam(data)  # data[7][iteration][fit][names]
            self._charge = self._unpack_prop(Q, data)[0][0]
            self._charge_std = self._unpack_prop(Q_STD, data)[0][0]
            self._r_matrix = self._unpack_prop(R_MAT, data)[0]  # List of r matrix per iteration
            self._twiss_0 = self._unpack_prop(TWISS_0, data) #data[14]  # No clue how these fields are arranged
            self._energy = self._unpack_prop(ENERGY, data)[0][0]  # GeV I believe
            self._twiss = self._unpack_prop(TWISS, data)
            self._twiss_std = self._unpack_prop(TWISS_STD, data)
            self._orbit = self._unpack_prop(ORBIT, data)
            self._orbit_std = self._unpack_prop(ORBIT_STD, data)
            self._twiss_pv = self._unpack_twiss_pv(data[20])
        except Exception as e:
            print('Error loading mat file: {0}'.format(e))

    @property
    def fields(self):
        return self._fields

    @property
    def mat_file(self):
        return self._file

    @property
    def status(self):
        return self._status

    @property
    def scan_type(self):
        return self._type

    @property
    def name(self):
        return self._name

    @property
    def quad_name(self):
        return self._quad_name

    @property
    def quad_val(self):
        return self._quad_val
    
    @property
    def use(self):
        return self._use

    @property
    def timestamp(self):
        return self._ts

    @property
    def beam(self):
        """list of dictionaries each iteration's stats"""
        if self._beam:
            return self._beam[0]
        return self._beam

    @property
    def charge(self):
        return self._charge

    @property
    def charge_std(self):
        return self._charge_std

    @property
    def rmat(self):
        """list of r matrix, one per iteration"""
        return self._r_matrix

    @property
    def twiss_0(self):
        return self._twiss_0

    @property
    def energy(self):
        return self._energy

    @property
    def twiss(self):
        return self._twiss

    @property
    def twiss_std(self):
        return self._twiss_std

    @property
    def orbit(self):
        return self._orbit

    @property
    def orbit_std(self):
        return self._orbit_std

    @property
    def emit_x(self):
        """Return dict of emit with fit as key"""
        emit_x = None
        if self._twiss_pv:
            emit_x = dict(zip(FIT, self._twiss_pv[0]['val']))
        return emit_x

    @property
    def beta_x(self):
        beta_x = None
        if self._twiss_pv:
            beta_x = dict(zip(FIT, self._twiss_pv[1]['val']))
        return beta_x

    @property
    def alpha_x(self):
        alpha_x = None
        if self._twiss_pv:
            alpha_x = dict(zip(FIT, self._twiss_pv[2]['val']))
        return alpha_x

    @property
    def bmag_x(self):
        bmag_x = None
        if self._twiss_pv:
            bmag_x = dict(zip(FIT, self._twiss_pv[3]['val']))
        return bmag_x

    @property
    def emit_y(self):
        emit_y = None
        if self._twiss_pv:
            emit_y = dict(zip(FIT, self._twiss_pv[4]['val']))
        return emit_y

    @property
    def beta_y(self):
        beta_y = None
        if self._twiss_pv:
            beta_y = dict(zip(FIT, self._twiss_pv[5]['val']))
        return beta_y

    @property
    def alpha_y(self):
        alpha_y = None
        if self._twiss_pv:
            alpha_y = dict(zip(FIT, self._twiss_pv[6]['val']))
        return alpha_y

    @property
    def bmag_y(self):
        bmag_y = None
        if self._twiss_pv:
            bmag_y = dict(zip(FIT, self._twiss_pv[7]['val']))
        return bmag_y

    def _unpack_prop(self, prop, data):
        if prop not in self._fields:
            return None

        idx = self._fields.index(prop)
        return data[idx]

    def _unpack_beam(self, data):
        """Unpacks to a list of lists.  Each list is an iteration which contains
        all the data for each fit.  Each fit is a dictionary with all the associated types of data.
        Also, since beam_std is a duplicate of beam except for stats I just throw the stats in the
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
                    iter_fit['stats_std'] = beam_std[i1][i2][10]
                else:
                    iter_fit['stats_std'] = []
                fit_list.append(iter_fit)
            temp.append(fit_list)
            
        return temp

    def _unpack_twiss_pv(self, twiss):
        """The other important piece.  All the twiss parameters from the
        emittance scan.  7 vals corresponding to each fit method"""
        if TWISS_PV not in self._fields:
            return None

        names = twiss.dtype.names
        temp1 = []
        for val in twiss:
            temp2 = dict()
            for i, name in enumerate(names):
                if name != 'egu':
                    if isinstance(val[0][i][0], unicode):
                        temp2[name] = str(val[0][i][0])
                    else:
                        temp2[name] = val[0][i][0] 
            temp1.append(temp2)

        return temp1
