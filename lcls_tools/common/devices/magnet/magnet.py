#!/usr/local/lcls/package/python/current/bin/python

import epics
from epics import PV
from dataclasses import dataclass, field
from typing import Dict
import lcls_tools.common.devices.magnet.magnet_constants as mc
from inspect import getmembers


### Decorators ###
def check_state(f):
    """Decorator to only allow transitions in 'Ready' state"""

    def decorated(self, *args, **kwargs):
        if self.ctrl_value != "Ready":
            print("Unable to perform action, magnet not in Ready state")
            return
        return f(self, *args, **kwargs)

    return decorated


class YAMLMagnet:
    name: str
    _bctrl: PV
    _bact: PV
    _bdes: PV
    _bcon: PV
    _ctrl: PV
    _length: float = None
    _b_tolerance: float = None
    control_information: Dict = None
    metadata: Dict = None

    def __init__(self, name=None, **kwargs):
        self.name = name
        [setattr(self, k, v) for k, v in kwargs.items()]
        # setup PVs and attributes
        [setattr(self, k, PV(v)) for k, v in self.control_information["PVs"].items()]
        # setup metadata and attributes
        [setattr(self, k, v) for k, v in self.metadata.items()]

    @_bctrl.setter
    @check_state
    def _bctrl(self, val):
        """Set bctrl value"""
        if not isinstance(val, float) or isinstance(val, int):
            print("you need to provide an in or float")
            return

        self._bctrl.put(val)

    @property
    def bact(self):
        """Get the BACT value"""
        return self._bact.get()

    @property
    def bdes(self):
        """Get BDES value"""
        return self._bdes.get()

    @property
    def ctrl_value(self):
        """Get the current action on magnet"""
        return self._ctrl_vars[self._ctrl.get()]

    @property
    def length(self):
        """Magnetic Length, should be from model"""
        return self._length

    @_length.setter
    def length(self, length):
        """Set the magnetic length for a magnet"""
        if not isinstance(length, float):
            print("You must provide a float for magnet length")
            return

        self._length = length

    @property
    def pv_props(self):
        """All the properties that are PV objects/can have callbacks"""
        return self._pv_props

    @property
    def b_tolerance(self):
        return self._b_tolerance

    @_b_tolerance.setter
    def tol(self, tol):
        """Set the magnetic length for a magnet"""
        if not isinstance(tol, float):
            print("You must provide a float for magnet tol")
            return False

        self._b_tolerance = tol

    @check_state
    def trim(self):
        """Issue trim command"""
        self._ctrl.put(mc.CTRL.index("TRIM"))

    @check_state
    def perturb(self):
        """Issue perturb command"""
        self._ctrl.put(mc.CTRL.index("PERTURB"))

    def con_to_des(self):
        """Issue con to des commands"""
        self._ctrl.put(mc.CTRL.index("BCOM_TO_BDES"))

    def save_bdes(self):
        """Save BDES"""
        self._ctrl.put(mc.CTRL.index("SAVE_BDES"))

    def load_bdes(self):
        """Load BDES"""
        self._ctrl.put(mc.CTRL.index("LOAD_BDES"))

    def undo_bdes(self):
        """Save BDES"""
        self._ctrl.put(mc.CTRL.index("UNDO_BDES"))

    @check_state
    def dac_zero(self):
        """DAC zero magnet"""
        self._ctrl.put(mc.CTRL.index("DAC_ZERO"))

    @check_state
    def calibrate(self):
        """Calibrate magnet"""
        self._ctrl.put(mc.CTRL.index("CALIB"))

    @check_state
    def standardize(self):
        """Standardize magnet"""
        self._ctrl.put(mc.CTRL.index("STDZ"))

    def reset(self):
        """Reset magnet"""
        self._ctrl.put(mc.CTRL.index("RESET"))


def get_magnets():
    """Return MAD names of all magenets that have models"""
    return mc.MAGNETS.keys()


class Magnet(object):
    """Magnet control"""

    def __init__(self, name="SOL1B"):
        if name not in mc.MAGNETS.keys():
            raise ValueError("You have not specified a valid magnet")
        mag_dict = mc.MAGNETS[name]
        self._name = name
        self._bctrl = PV(mag_dict["bctrl"])
        self._bact = PV(mag_dict["bact"])
        self._bdes = PV(mag_dict["bdes"])
        self._bcon = PV(mag_dict["bcon"])
        self._ctrl = PV(mag_dict["ctrl"])
        self._tol = mag_dict["tol"]
        self._length = mag_dict["length"]
        self._ctrl_vars = self._ctrl.get_ctrlvars()["enum_strs"]
        self._pv_attrs = self.find_pv_attrs()

    def check_state(f):
        """Decorator to only allow transitions in 'Ready' state"""

        def decorated(self, *args, **kwargs):
            if self.ctrl_value != "Ready":
                print("Unable to perform action, magnet not in Ready state")
                return
            return f(self, *args, **kwargs)

        return decorated

    @property
    def name(self):
        """Get the magnet name"""
        return self._name

    @property
    def bctrl(self):
        """Get BCTRL value"""
        return self._bctrl.get()

    @bctrl.setter
    @check_state
    def bctrl(self, val):
        """Set bctrl value"""
        if not isinstance(val, float) or isinstance(val, int):
            print("you need to provide an in or float")
            return

        self._bctrl.put(val)

    @property
    def bact(self):
        """Get the BACT value"""
        return self._bact.get()

    @property
    def bdes(self):
        """Get BDES value"""
        return self._bdes.get()

    @property
    def ctrl_value(self):
        """Get the current action on magnet"""
        return self._ctrl_vars[self._ctrl.get()]

    @property
    def length(self):
        """Magnetic Length, should be from model"""
        return self._length

    @length.setter
    def length(self, length):
        """Set the magnetic length for a magnet"""
        if not isinstance(length, float):
            print("You must provide a float for magnet length")
            return

        self._length = length

    @property
    def pv_props(self):
        """All the properties that are PV objects/can have callbacks"""
        return self._pv_props

    @property
    def tol(self):
        return self._tol

    @tol.setter
    def tol(self, tol):
        """Set the magnetic length for a magnet"""
        if not isinstance(tol, float):
            print("You must provide a float for magnet tol")
            return False

        self._tol = tol

    @check_state
    def trim(self):
        """Issue trim command"""
        self._ctrl.put(mc.CTRL.index("TRIM"))

    @check_state
    def perturb(self):
        """Issue perturb command"""
        self._ctrl.put(mc.CTRL.index("PERTURB"))

    def con_to_des(self):
        """Issue con to des commands"""
        self._ctrl.put(mc.CTRL.index("BCOM_TO_BDES"))

    def save_bdes(self):
        """Save BDES"""
        self._ctrl.put(mc.CTRL.index("SAVE_BDES"))

    def load_bdes(self):
        """Load BDES"""
        self._ctrl.put(mc.CTRL.index("LOAD_BDES"))

    def undo_bdes(self):
        """Save BDES"""
        self._ctrl.put(mc.CTRL.index("UNDO_BDES"))

    @check_state
    def dac_zero(self):
        """DAC zero magnet"""
        self._ctrl.put(mc.CTRL.index("DAC_ZERO"))

    @check_state
    def calibrate(self):
        """Calibrate magnet"""
        self._ctrl.put(mc.CTRL.index("CALIB"))

    @check_state
    def standardize(self):
        """Standardize magnet"""
        self._ctrl.put(mc.CTRL.index("STDZ"))

    def reset(self):
        """Reset magnet"""
        self._ctrl.put(mc.CTRL.index("RESET"))

    def find_pv_attrs(self):
        """Get all the PV object attributes"""
        pv_attrs = []
        for mem in getmembers(self):
            if len(mem) > 1 and isinstance(mem[1], PV):
                pv_attrs.append(mem[0])

        return pv_attrs

    ################## Actions #################

    def add_clbk(self, fn, attr="_bact"):
        """Add a callback function to a given attribute"""
        if attr not in self._pv_attrs:
            print("this attribute is not a pv object, ignored")
            return

        fns = [val[0] for val in getattr(self, attr).callbacks.values()]

        if fn in fns:
            print("this is a duplicate callback assignment, ignored")
            return

        print("adding callback {0}".format(fn))
        getattr(self, attr).add_callback(fn, with_ctrlvars=False)

    def remove_clbk(self, fn, attr="_bact"):
        """Add a callback function to a given attribute"""
        if attr not in self._pv_attrs:
            print("this attribute is not a pv object, ignored")
            return

        index = None
        for k, v in getattr(self, attr).callbacks.items():
            if v[0] == fn:
                index = k

        if not index:
            print("function not found in callbacks, ignored")
            return

        print("remvong callback {0}".format(fn))
        getattr(self, attr).remove_callback(index=index)
