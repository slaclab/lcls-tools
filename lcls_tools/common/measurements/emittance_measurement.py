import sys
import time
import enum
from typing import Any, List, Optional

import numpy as np
from numpy import ndarray
from pydantic import (
    BaseModel,
    ConfigDict,
    PositiveInt,
    SerializeAsAny,
    field_validator,
    PositiveFloat,
)

from lcls_tools.common.data.emittance import compute_emit_bmag
from lcls_tools.common.data.model_general_calcs import bdes_to_kmod, get_optics
from lcls_tools.common.devices.magnet import Magnet
from lcls_tools.common.measurements.measurement import Measurement
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType


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


class EmittanceMeasurementResult(BaseModel):
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

    model_config = ConfigDict(arbitrary_types_allowed=True)

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


class QuadScanEmittance(Measurement):
    """Use a quad and profile monitor/wire scanner to perform an emittance measurement

    Arguments:
    ------------------------
    energy: float
        Beam energy in GeV
    scan_values: List[float]
        BDES values of magnet to scan over
    magnet: Magnet
        Magnet object used to conduct scan
    beamsize_measurement: BeamsizeMeasurement
        Beamsize measurement object from profile monitor/wire scanner
    n_measurement_shots: int
        number of beamsize measurements to make per individual quad strength
    rmat: ndarray, optional
        Transport matricies for the horizontal and vertical phase space from
        the end of the scanning magnet to the screen, array shape should be 2 x 2 x 2 (
        first element is the horizontal transport matrix, second is the vertical),
        if not provided meme is used to calculate the transport matricies
    design_twiss: dict[str, float], optional
        Dictionary containing design twiss values with the following keys (`beta_x`,
        `beta_y`, `alpha_x`, `alpha_y`) where the beta/alpha values are in units of [m]/[]
        respectively
    beam_sizes, dict[str, list[float]], optional
        Dictionary contraining X-rms and Y-rms beam sizes (keys:`rms_x`,`rms_y`)
        measured during the quadrupole scan in units of [m].
    wait_time, float, optional
        Wait time in seconds between changing quadrupole settings and making beamsize
        measurements.

    Methods:
    ------------------------
    measure: does the quad scan, getting the beam sizes at each scan value,
    gets the rmat and twiss parameters, then computes and returns the emittance and BMAG

    measure_beamsize: take measurement from measurement device, store beam sizes
    """

    energy: float
    scan_values: list[float]
    magnet: Magnet
    beamsize_measurement: Measurement
    n_measurement_shots: PositiveInt = 1
    _info: Optional[list] = []

    rmat: Optional[ndarray] = None
    design_twiss: Optional[dict] = None  # design twiss values

    wait_time: PositiveFloat = 5.0

    name: str = "quad_scan_emittance"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("rmat")
    def validate_rmat(cls, v, info):
        assert v.shape == (2, 2, 2)
        return v

    def measure(self):
        """
        Conduct quadrupole scan to measure the beam phase space.

        Returns:
        -------
        result : EmittanceMeasurementResult
            Object containing the results of the emittance measurement
        """

        # scan magnet strength and measure beamsize
        self.perform_beamsize_measurements()

        # extract beam sizes from info
        beam_sizes = self._get_beamsizes_from_info()

        # get scan values
        scan_values = np.array(self.scan_values)

        # get transport matrix and design twiss values from meme
        # TODO: get settings from arbitrary methods (ie. not meme)
        if self.rmat is None and self.design_twiss is None:
            optics = get_optics(
                self.magnet_name,
                self.device_measurement.device.name,
            )

            self.rmat = optics["rmat"]
            self.design_twiss = optics["design_twiss"]

        magnet_length = self.magnet.metadata.l_eff
        if magnet_length is None:
            raise ValueError(
                "magnet length needs to be specified for magnet "
                f"{self.magnet.name} to be used in emittance measurement"
            )

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
            single_beam_size = beam_sizes[i][~np.isnan(beam_sizes[i])]
            beam_size_squared = (single_beam_size * 1e3) ** 2
            kmod = bdes_to_kmod(
                self.energy, magnet_length, scan_values[~np.isnan(beam_sizes[i])]
            )

            # negate for y
            if i == 1:
                kmod = -1 * kmod

            # compute emittance and bmag
            result = compute_emit_bmag(
                k=kmod,
                beamsize_squared=beam_size_squared.T,
                q_len=magnet_length,
                rmat=self.rmat[i],
                twiss_design=twiss_betas_alphas[i]
                if twiss_betas_alphas is not None
                else None,
            )
            result.update({"quadrupole_focusing_strengths": kmod})
            result.update(
                {"quadrupole_pv_values": scan_values[~np.isnan(beam_sizes[i])]}
            )

            # add results to dict object
            for name, value in result.items():
                if name == "bmag" and value is None:
                    continue
                else:
                    results[name].append(value)

            results["rms_beamsizes"].append(single_beam_size)

        results.update({"info": self._info})
        results.update({"metadata": self.model_dump()})

        # collect information into EmittanceMeasurementResult object
        return EmittanceMeasurementResult(**results)

    def perform_beamsize_measurements(self):
        """Perform the beamsize measurements"""
        self.magnet.scan(scan_settings=self.scan_values, function=self.measure_beamsize)

    def measure_beamsize(self):
        """
        Take measurement from measurement device,
        and store results in `self._info`
        """
        time.sleep(self.wait_time)

        result = self.beamsize_measurement.measure(self.n_measurement_shots)
        self._info += [result]

    def _get_beamsizes_from_info(self) -> ndarray:
        """
        Extract the mean rms beam sizes from the info list, units in meters.
        """
        beam_sizes = []
        for result in self._info:
            beam_sizes.append(
                np.mean(result.rms_sizes, axis=0)
                * self.beamsize_measurement.device.resolution
                * 1e-6
            )

        return np.array(beam_sizes).T


class MultiDeviceEmittance(Measurement):
    name: str = "multi_device_emittance"

    def measure(self):
        raise NotImplementedError("Multi-device emittance not yet implemented")
