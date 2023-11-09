import scipy.constants as sc
import numpy as np
from numpy.linalg import pinv
from math import sin, cos, sqrt

# L - magnetic length of solenoid
# Bo - magnetic filed strength in solenoid
# Bp = Beta*gamma*m*c (beam momentum)
# gamma = 1 + (Egun / Eo)
# beta = sqrt(1 + (1/gamma)^2)
# d - distance from sol exit and bpm
# c = cos(KL)
# s = sin(KL)
# K = Bo / (2Bp)

# Convert kG to Tesla Bt = BkG / 10

# General scheme: Generate x and y rows for each solenoid setting,
# This is a one off class.  For each scan instantiate a new SolCorrection object
# This was done for simplicity, but we can think about reusing or data manipulation
# if that becomes a need.  There is NO error checking currently, so if you call
# a public function referencing a private class var that is None, you'll get an
# error or None.  This will be fixed when I care enough to fix it


class SolCalc(object):
    def __init__(self, l_eff, e_gun, d):
        self._l = l_eff  # Leff
        self._e_gun = e_gun  # MeV
        self._d = d  # distance from sol exit and bpm
        self._K = None
        self._c = None
        self._s = None
        self._x_arrays = None
        self._y_arrays = None
        self._results = None
        self._x_vals = []
        self._x_stds = []
        self._y_stds = []
        self._y_vals = []
        self._b_vals = []

    @property
    def x_vals(self):
        return self._x_vals

    @property
    def y_vals(self):
        return self._y_vals

    @property
    def x_stds(self):
        return self._x_stds

    @property
    def y_stds(self):
        return self._y_stds

    @property
    def b_vals(self):
        return self._b_vals

    @property
    def results(self):
        return self._results

    @property
    def gun_energy(self):
        return self._e_gun

    @property
    def length(self):
        return self._l

    @property
    def distance(self):
        return self._d

    def calc_p(self):
        """momentum calculation"""
        gamma = 1.0 + (self._e_gun / 0.511)
        beta = sqrt(1.0 - (1 / gamma) ** 2)
        return beta * gamma * sc.m_e * sc.c

    def calc_K(self, b, p):
        """Get the current K value"""
        return (b * sc.e) / (2 * p)

    def calc_c(self):
        """c term"""
        return cos(self._K * self._l)

    def calc_s(self):
        """s term"""
        return sin(self._K * self._l)

    def x1(self):
        """first term, x"""
        return self._c**2 - self._d * self._K * self._s * self._c

    def x2(self):
        """second term, x"""
        return self._s * self._c * (1 / self._K) + self._d * self._c**2

    def x3(self):
        """third term, x"""
        return self._s * self._c - self._d * self._K * self._s**2

    def x4(self):
        """fourth term, x"""
        return self._s**2 * (1 / self._K) + self._d * self._s * self._c

    def x5(self):
        """Default"""
        return 1

    def x6(self):
        """Default"""
        return 0

    def y1(self):
        """first term y"""
        return -self._s * self._c + self._d * self._K * self._s**2

    def y2(self):
        """second term y"""
        return -self._s**2 * (1 / self._K) - self._d * self._s * self._c

    def y3(self):
        """third term y"""
        return self._c**2 - self._d * self._K * self._s * self._c

    def y4(self):
        """fourth term y"""
        return self._s * self._c * (1 / self._K) + self._d * self._c**2

    def y5(self):
        """Default"""
        return 0

    def y6(self):
        """Default"""
        return 1

    def _calc_props(self, b):
        """Update all the properties
        b (float): magnetic field in kG
        """
        b /= 10.0  # T
        self._b_vals.append(b)
        p = self.calc_p()
        self._K = self.calc_K(b, p)
        self._c = self.calc_c()
        self._s = self.calc_s()

    def add_data(self, x_val, y_val, x_std, y_std, b):
        """Add the data from a new scan, calculate new rows for x and y"""
        self._calc_props(b)
        self._x_vals.append(x_val)
        self._y_vals.append(y_val)
        self._x_stds.append(x_std)
        self._y_stds.append(y_std)

        if self._x_arrays is not None:
            self._x_arrays = np.vstack((self._x_arrays, self.gen_x_arr()))
        else:
            self._x_arrays = self.gen_x_arr()

        if self._y_arrays is not None:
            self._y_arrays = np.vstack((self._y_arrays, self.gen_y_arr()))
        else:
            self._y_arrays = self.gen_y_arr()

    def gen_x_arr(self):
        """The x array froma single measurement"""
        arr = np.array(
            [self.x1(), self.x2(), self.x3(), self.x4(), self.x5(), self.x6()]
        )

        return arr

    def gen_y_arr(self):
        """The y array from single measurement"""
        arr = np.array(
            [self.y1(), self.y2(), self.y3(), self.y4(), self.y5(), self.y6()]
        )

        return arr

    def calc_offsets(self):
        """Solve the problem"""
        self._results = pinv(np.vstack((self._x_arrays, self._y_arrays)))
        return self._results
