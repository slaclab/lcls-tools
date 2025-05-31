from abc import abstractmethod
import sys
import time
import enum
from typing import Any, List, Optional

import numpy as np
from numpy import ndarray
from pydantic import (
    ConfigDict,
    PositiveInt,
    SerializeAsAny,
    field_validator,
    PositiveFloat,
)
import yaml

from lcls_tools.common.data.emittance import (
    compute_emit_bmag,
)
from lcls_tools.common.data.model_general_calcs import bdes_to_kmod, get_optics
from lcls_tools.common.devices.magnet import Magnet
from lcls_tools.common.measurements.measurement import Measurement
from lcls_tools.common.measurements.screen_profile import (
    ScreenBeamProfileMeasurement,
    ScreenBeamProfileMeasurementResult,
)
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
import lcls_tools
from lcls_tools.common.measurements.wire_scan import (
    WireBeamProfileMeasurement,
    WireBeamProfileMeasurementResult,
)


class BMAGMode(enum.IntEnum):
    X = 0
    Y = 1
    # Value is not a valid index unlike X & Y
    GEOMETRIC_MEAN = -sys.maxsize

    @classmethod
    def from_any(cls, value):
        def _members():
            return ", ".join((m.name for m in cls))

        try:
            if isinstance(value, cls):
                return value
            if isinstance(value, str):
                return cls[value.upper()]
            if isinstance(value, int):
                return cls(value)
        except (ValueError, KeyError):
            pass
        raise ValueError(f"invalid {cls.__name__}={value} must be one of: {_members()}")


class EmittanceMeasurementResult(lcls_tools.common.BaseModel):
    """
    EmittanceMeasurementResult stores the results of an emittance measurement.

    Attributes
    ----------
    quadrupole_focusing_strengths : List[ndarray]
        Quadrupole focusing strength (k1) settings of the quadrupole used in the scan in m^{-2}.
    quadrupole_pv_values : List[ndarray]
        Quadrupole PV control values used in the measurement.
    emittance : shape (2,)
        The geometric emittance values for x/y in mm-mrad.
    bmag : List[ndarray], Optional
        The BMAG values for x/y for each quadrupole strength.
    twiss_at_screen : List[ndarray]
        Twiss parameters (beta, alpha, gamma) calculated at the screen for each quadrupole strength in each plane.
    rms_beamsizes : List[ndarray]
        The RMS beam sizes for each quadrupole strength in each plane in meters.
    beam_matrix : array, shape (2,3)
        Reconstructed beam matrix at the entrance of the quadrupole for
        both x/y directions. Elements correspond to (s11,s12,s22) of the beam matrix.
    info : Any
        Metadata information related to the measurement.

    """

    quadrupole_focusing_strengths: List[NDArrayAnnotatedType]
    quadrupole_pv_values: List[NDArrayAnnotatedType]
    emittance: NDArrayAnnotatedType
    bmag: Optional[List[NDArrayAnnotatedType]] = None
    twiss_at_screen: List[NDArrayAnnotatedType]
    rms_beamsizes: List[NDArrayAnnotatedType]
    beam_matrix: NDArrayAnnotatedType
    metadata: SerializeAsAny[Any]

    def get_best_bmag(self, mode=BMAGMode.GEOMETRIC_MEAN) -> tuple:
        """
        Get the best BMAG value for a given mode (x, y, geometric mean) and the corresponding PV value.

        Parameters
        ----------
        mode : str, optional
            The mode to get the best BMAG value for, default is "geometric_mean".
            Mode can be one of the following: "x", "y", "geometric_mean".
            - "x": get the best BMAG value for the x plane.
            - "y": get the best BMAG value for the y plane.
            - "geometric_mean": get the best BMAG value for the geometric mean of the x and y planes.

        Returns
        -------
        tuple
            The best BMAG value and corresponding pv value for the quadrupole.

        """
        if self.bmag is None:
            raise ValueError("BMAG values are not available for this measurement")

        mode = BMAGMode.from_any(mode)

        bmag = self.bmag
        if mode == BMAGMode.GEOMETRIC_MEAN:
            # if calculating the geometric mean, we need to interpolate between samples
            fits = []

            min_k = min([min(k) for k in self.quadrupole_pv_values])
            max_k = max([max(k) for k in self.quadrupole_pv_values])
            k = np.linspace(min_k, max_k, 100)
            for i in range(2):
                bmag_fit = np.polyfit(self.quadrupole_pv_values[i], bmag[i], 2)
                fits.append(np.polyval(bmag_fit, k))

            # multiply x and y bmag values to get geometric mean
            bmag = np.sqrt(fits[0] * fits[1])

            # get best index and return bmag value and corresponding pv value
            best_index = np.argmin(bmag)
            bmag_value = bmag[best_index]
            best_pv_value = k[best_index]

        else:
            best_index = np.argmin(bmag[mode.value])
            bmag_value = bmag[mode.value][best_index]
            best_pv_value = self.quadrupole_pv_values[mode.value][best_index]

        return bmag_value, best_pv_value


class EmittanceMeasurementBase(Measurement):
    """Base class to perform an emittance measurement

    Arguments:
    ------------------------
    energy: float
        Beam energy in GeV
    n_measurements: int
        number of beamsize measurements to make for each phase advance
    rmat: ndarray, optional
        Transport matricies for the horizontal and vertical phase space from
        the end of the scanning magnet to the screen, array shape should be 2 x 2 x 2 (
        first element is the horizontal transport matrix, second is the vertical),
        if not provided meme is used to calculate the transport matricies
    design_twiss: dict[str, float], optional
        Dictionary containing design twiss values with the following keys (`beta_x`,
        `beta_y`, `alpha_x`, `alpha_y`) where the beta/alpha values are in units of [m]/[]
        respectively
    wait_time, float, optional
        Wait time in seconds between making beamsize measurements.

    Other Attributes:
    ------------------------
    _info
        List of raw beam size measurement results

    Methods:
    ------------------------
    measure: performs beam size measurements at each phase advance, gets the beam sizes,
    gets the rmat and twiss parameters, then computes and returns the emittance and BMAG

    measure_beamsize: take measurement from measurement device, store beam sizes
    """

    energy: float
    n_measurements: PositiveInt = 1

    rmat: Optional[ndarray] = None
    design_twiss: Optional[dict] = None  # design twiss values

    wait_time: PositiveFloat = 5.0

    _info: Optional[list] = []

    name: str = "emittance_measurement_base"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("rmat")
    def validate_rmat(cls, v, info):
        assert v.shape == (2, 2, 2)
        return v

    def measure(self):
        """
        Measure the beam phase space.

        Returns:
        -------
        result : EmittanceMeasurementResult
            Object containing the results of the emittance measurement
        """

        self._perform_beamsize_measurements()

        # extract beam sizes from info
        beam_sizes = self._get_beamsizes_from_info()

        self._get_rmat_and_design_twiss()

        # organize data into arrays for use in `compute_emit_bmag`
        # rmat = np.stack([self.rmat[0:2, 0:2], self.rmat[2:4, 2:4]])
        if self.design_twiss:
            twiss_betas_alphas = np.array(
                [
                    [self.design_twiss["beta_x"], self.design_twiss["alpha_x"]],
                    [self.design_twiss["beta_y"], self.design_twiss["alpha_y"]],
                ]
            )

        else:
            twiss_betas_alphas = None

        # fit scans independently for x/y
        # only keep data that has non-nan beam sizes -- independent for x/y
        results = {
            "emittance": [],
            "twiss_at_screen": [],
            "beam_matrix": [],
            "bmag": [] if twiss_betas_alphas is not None else None,
            "quadrupole_focusing_strengths": [],
            "quadrupole_pv_values": [],
            "rms_beamsizes": [],
        }

        for i in range(2):
            # get rid of NaNs
            idx = ~np.isnan(beam_sizes[i])
            beam_sizes_i = beam_sizes[i][idx]

            # convert beam sizes to units of mm^2
            beam_sizes_squared = (beam_sizes_i * 1e3) ** 2

            # create dict of arguments for compute_emit_bmag
            emit_kwargs = {
                "beamsize_squared": beam_sizes_squared.T,
                "rmat": self.rmat[i],
                "twiss_design": twiss_betas_alphas[i]
                if twiss_betas_alphas is not None
                else None,
            }

            kmod, scan_values = self._get_kmod_and_scan_values(i, beam_sizes)

            # modify arguments and results for quad scan measurements
            if kmod is not None:
                emit_kwargs["k"] = kmod
                emit_kwargs["q_len"] = self._get_magnet_length()
                results["quadrupole_focusing_strengths"].append(kmod)
                results["quadrupole_pv_values"].append(scan_values)

            # compute emittance and bmag
            result = compute_emit_bmag(**emit_kwargs)

            # add results to dict object
            for name, value in result.items():
                if name == "bmag" and value is None:
                    continue
                else:  # beam matrix and emittance get appended
                    results[name].append(value)

            results["rms_beamsizes"].append(beam_sizes_i)

        results.update({"metadata": self.model_dump()})

        # collect information into EmittanceMeasurementResult object
        return EmittanceMeasurementResult(**results)

    def measure_beamsize(self, beamsize_measurement):
        """
        Take measurement from measurement device,
        and store results in `self._info`
        """
        time.sleep(self.wait_time)

        if isinstance(beamsize_measurement, ScreenBeamProfileMeasurement):
            result = beamsize_measurement.measure(self.n_measurements)
        elif isinstance(beamsize_measurement, WireBeamProfileMeasurement):
            result = beamsize_measurement.measure()
        else:
            raise ValueError("Unknown beamsize measurement type")
        self._info += [result]

    @abstractmethod
    def _perform_beamsize_measurements(self):
        pass

    def _get_beamsizes_from_info(self) -> ndarray:
        """
        Extract the mean rms beam sizes from the info list, units in meters.
        """
        beam_sizes = []
        for result in self._info:
            if isinstance(result, ScreenBeamProfileMeasurementResult):
                beam_sizes.append(np.mean(result.rms_sizes, axis=0) * 1e-6)
            elif isinstance(result, WireBeamProfileMeasurementResult):
                # Get rms size from default detector for wire
                with open("../devices/yaml/wire_lblms.yaml", "r") as wire_lblms_yaml:
                    wire_lblms = yaml.safe_load(wire_lblms_yaml)
                wire = result.metadata["my_wire"].name
                lblm = wire_lblms[wire]
                beam_sizes.append(result.rms_sizes[lblm] * 1e-6)
            else:
                raise ValueError("Unknown beamsize measurement result type")

        return np.array(beam_sizes).T

    @abstractmethod
    def _get_rmat_and_design_twiss(self):
        pass

    def _get_magnet_length(self):
        return None

    def _get_kmod_and_scan_values(self, i, beam_sizes):
        return None, None


class QuadScanEmittance(EmittanceMeasurementBase):
    """Use a quad and profile monitor/wire scanner to perform an emittance measurement

    Arguments:
    ------------------------
    energy: float
        Beam energy in GeV
    n_measurements: int
        number of beamsize measurements to make per individual quad strength
    scan_values: List[float]
        BDES values of magnet to scan over
    magnet: Magnet
        Magnet object used to conduct scan
    beamsize_measurement: BeamsizeMeasurement
        Beamsize measurement object from profile monitor/wire scanner
    rmat: ndarray, optional
        Transport matricies for the horizontal and vertical phase space from
        the end of the scanning magnet to the screen, array shape should be 2 x 2 x 2 (
        first element is the horizontal transport matrix, second is the vertical),
        if not provided meme is used to calculate the transport matricies
    design_twiss: dict[str, float], optional
        Dictionary containing design twiss values with the following keys (`beta_x`,
        `beta_y`, `alpha_x`, `alpha_y`) where the beta/alpha values are in units of [m]/[]
        respectively
    wait_time, float, optional
        Wait time in seconds between changing quadrupole settings and making beamsize
        measurements.

    Methods:
    ------------------------
    measure: does the quad scan, getting the beam sizes at each scan value,
    gets the rmat and twiss parameters, then computes and returns the emittance and BMAG

    measure_beamsize: take measurement from measurement device, store beam sizes
    """

    scan_values: list[float]
    magnet: Magnet
    beamsize_measurement: Measurement

    wait_time: PositiveFloat = 1.0

    name: str = "quad_scan_emittance"

    @field_validator("rmat")
    def validate_rmat(cls, v, info):
        assert v.shape == (2, 2, 2)
        return v

    def _perform_beamsize_measurements(self):
        self.magnet.scan(
            scan_settings=self.scan_values, function=self._measure_beamsize
        )

    def _measure_beamsize(self):
        self.measure_beamsize(self.beamsize_measurement)

    def _get_rmat_and_design_twiss(self):
        """
        Get transport matrix and design twiss values from meme
        """
        # TODO: get settings from arbitrary methods (ie. not meme)
        if self.rmat is None and self.design_twiss is None:
            optics = get_optics(
                self.magnet.name,
                self.beamsize_measurement.device.name,
            )

            self.rmat = optics["rmat"]
            self.design_twiss = optics["design_twiss"]

    def _get_magnet_length(self):
        magnet_length = self.magnet.metadata.l_eff
        if magnet_length is None:
            raise ValueError(
                "magnet length needs to be specified for magnet "
                f"{self.magnet.name} to be used in emittance measurement"
            )

        return magnet_length

    def _get_kmod_and_scan_values(self, i, beam_sizes):
        # Create two copies of quad scan values and stack together
        scan_values = np.tile(np.array(self.scan_values), (2, 1))

        # Get rid of NaNs
        idx = ~np.isnan(beam_sizes[i])
        scan_values_i = scan_values[i][idx]

        # Quad values to kmod values
        kmod = bdes_to_kmod(
            self.energy,
            self._get_magnet_length(),
            scan_values_i,
        )

        # negate for y
        if i == 1:
            kmod = -1 * kmod

        return kmod, scan_values_i


class MultiDeviceEmittance(EmittanceMeasurementBase):
    """Uses multiple profile monitors/wire scanners to perform an emittance measurement

    Arguments:
    ------------------------
    energy: float
        Beam energy in GeV
    n_measurements: int
        number of beamsize measurements to make for each beam size measurement device
    beamsize_measurements: List[BeamsizeMeasurement]
        List of beamsize measurement objects from profile monitors/wire scanners
    rmat: ndarray, optional
        Transport matricies for the horizontal and vertical phase space from
        the end of the scanning magnet to the screen, array shape should be 2 x 2 x 2 (
        first element is the horizontal transport matrix, second is the vertical),
        if not provided meme is used to calculate the transport matricies
    design_twiss: dict[str, float], optional
        Dictionary containing design twiss values with the following keys (`beta_x`,
        `beta_y`, `alpha_x`, `alpha_y`) where the beta/alpha values are in units of [m]/[]
        respectively
    wait_time, float, optional
        Wait time in seconds between making beamsize measurements.

    Methods:
    ------------------------
    measure: gets the beam sizes at each beam size measurement device,
    gets the rmat and twiss parameters, then computes and returns the emittance and BMAG

    measure_beamsize: take measurement from measurement device, store beam sizes
    """

    beamsize_measurements: list[Measurement]

    name: str = "multi_device_emittance"

    @field_validator("rmat")
    def validate_rmat(cls, v, info):
        assert v.shape == (2, 2, 2)
        return v

    def _perform_beamsize_measurements(self):
        """Perform the beamsize measurements"""
        for beamsize_measurement in self.beamsize_measurements:
            self.measure_beamsize(beamsize_measurement)

    def _get_rmat_and_design_twiss(self):
        # TODO: write for multi device measurement
        raise NotImplementedError("This method is not implemented yet")
