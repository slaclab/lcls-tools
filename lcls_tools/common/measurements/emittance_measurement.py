from abc import abstractmethod
import time
import enum
from typing import Any, List, Optional

import numpy as np
from pydantic import (
    ConfigDict,
    SerializeAsAny,
    field_validator,
    PositiveFloat,
)

from lcls_tools.common.data.emittance import compute_emit_bmag
from lcls_tools.common.devices.magnet import Magnet
from lcls_tools.common.measurements.measurement import Measurement
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
from lcls_tools.common.data.model_general_calcs import (
    build_quad_rmat,
    bdes_to_kmod,
)
import lcls_tools

from lcls_tools.common.measurements.beam_profile import BeamProfileMeasurement


class BMAGMode(enum.IntEnum):
    X = 0
    Y = 1
    # Value is not a valid index unlike X & Y
    GEOMETRIC_MEAN = -10
    JOINT_MAX = -11

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
    emittance : shape (2,)
        The geometric emittance values for x/y in mm-mrad.
    bmag : List[ndarray], Optional
        The BMAG values for x/y for each beamsize measurement.
    twiss : List[ndarray]
        Twiss parameters (beta, alpha, gamma) calculated for each beamsize measurement.
    beamsizes : List[ndarray]
        The RMS beam sizes for each beamsize measurement in each plane in meters.
    beam_matrix : array, shape (2,3)
        Reconstructed beam matrix for both x/y directions.
        Elements correspond to (s11,s12,s22) of the beam matrix.
    info : Any
        Metadata information related to the measurement.

    """

    emittance: NDArrayAnnotatedType
    bmag: Optional[List[NDArrayAnnotatedType]] = None
    twiss: List[NDArrayAnnotatedType]
    beamsizes: List[NDArrayAnnotatedType]
    beam_matrix: NDArrayAnnotatedType
    metadata: SerializeAsAny[Any]


class QuadScanEmittanceResult(EmittanceMeasurementResult):
    """
    EmittanceMeasurementResult stores the results of an emittance measurement.

    Attributes
    ----------
    quadrupole_focusing_strengths : List[ndarray]
        Quadrupole focusing strength (k1) settings of the quadrupole used in the scan in m^{-2}.
    quadrupole_pv_values : List[ndarray]
        Quadrupole PV control values used in the measurement.

    Inherited Attributes
    ----------
    emittance : shape (2,)
        The geometric emittance values for x/y in mm-mrad.
    bmag : List[ndarray], Optional
        The BMAG values for x/y for each quadrupole strength.
    twiss : List[ndarray]
        Twiss parameters (beta, alpha, gamma) calculated at the screen for each quadrupole strength in each plane.
    beamsizes : List[ndarray]
        The RMS beam sizes for each quadrupole strength in each plane in meters.
    beam_matrix : array, shape (2,3)
        Reconstructed beam matrix at the entrance of the quadrupole for
        both x/y directions. Elements correspond to (s11,s12,s22) of the beam matrix.
    info : Any
        Metadata information related to the measurement.

    """

    quadrupole_focusing_strengths: List[NDArrayAnnotatedType]
    quadrupole_pv_values: List[NDArrayAnnotatedType]

    def get_best_bmag(self, mode=BMAGMode.GEOMETRIC_MEAN) -> tuple:
        """
        Get the best BMAG value for a given mode (x, y, geometric mean) and the corresponding PV value.

        Parameters
        ----------
        mode : str, optional
            The mode to get the best BMAG value for, default is "geometric_mean".
            Mode can be one of the following: "x", "y", "geometric_mean", "joint_max".
            - "x": get the best BMAG value for the x plane.
            - "y": get the best BMAG value for the y plane.
            - "geometric_mean": get the best BMAG value for the geometric mean of the x and y planes.
            - "joint_max": get the best BMAG value for the joint max of the x and y planes.

        Returns
        -------
        tuple
            The best BMAG value and corresponding pv value for the quadrupole.

        """
        if self.bmag is None:
            raise ValueError("BMAG values are not available for this measurement")

        mode = BMAGMode.from_any(mode)

        bmag = self.bmag

        if mode == BMAGMode.GEOMETRIC_MEAN or mode == BMAGMode.JOINT_MAX:
            # interpolate between samples
            fits = []

            min_k = min([min(k) for k in self.quadrupole_pv_values])
            max_k = max([max(k) for k in self.quadrupole_pv_values])
            k = np.linspace(min_k, max_k, 100)
            for i in range(2):
                bmag_fit = np.polyfit(self.quadrupole_pv_values[i], bmag[i], 2)
                fits.append(np.polyval(bmag_fit, k))
            if mode == BMAGMode.GEOMETRIC_MEAN:
                # multiply x and y bmag values to get geometric mean
                bmag = np.sqrt(fits[0] * fits[1])
            elif mode == BMAGMode.JOINT_MAX:
                # get the joint max of the x and y bmag values
                bmag = np.max(fits, axis=0)
        else:
            # get x or y bmag values individually
            bmag = bmag[mode.value]
            k = self.quadrupole_pv_values[mode.value]

        # get best index and return bmag value and corresponding pv value
        best_index = np.argmin(bmag)
        bmag_value = bmag[best_index]
        best_pv_value = k[best_index]

        return bmag_value, best_pv_value


class EmittanceMeasurementBase(Measurement):
    """Base class to perform an emittance measurement

    Arguments:
    ------------------------
    energy: float
        Beam energy in GeV
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

    wait_time: PositiveFloat = 5.0

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

        beamsize_results = self.perform_beamsize_measurements()

        rmats, design_twiss = self.setup_rmats_and_design_twiss()

        return self.calculate_emittance(beamsize_results, rmats, design_twiss)

    @abstractmethod
    def perform_beamsize_measurements(self):
        """

        Perform a beam size measurement at each point.
        Stores

        """
        pass

    @abstractmethod
    def setup_rmats_and_design_twiss(self):
        pass

    @abstractmethod
    def calculate_emittance(
        self, beamsize_results, rmats, design_twiss
    ) -> EmittanceMeasurementResult:
        """

        Calculate the emittance from the measured beam sizes, rmats and twiss.

        Returns:
        -------
        result : EmittanceMeasurementResult
            Object containing the results of the emittance measurement

        """

        pass


class QuadScanEmittance(EmittanceMeasurementBase):
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

    Other Attributes:
    ------------------------
    _info
        List of raw beam size measurement results

    Methods:
    ------------------------
    measure: does the quad scan, getting the beam sizes at each scan value,
    gets the rmat and twiss parameters, then computes and returns the emittance and BMAG

    measure_beamsize: take measurement from measurement device, store beam sizes
    """

    scan_values: list[float]
    magnet: Magnet
    beamsize_measurement: BeamProfileMeasurement

    name: str = "quad_scan_emittance"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("rmat")
    def validate_rmat(cls, v, info):
        assert v.shape == (2, 2, 2)
        return v

    def perform_beamsize_measurements(self):
        """Perform the beamsize measurements using a basic quadrupole scan."""
        beamsize_results = []
        # at each scan value, measure the beam size and store the result in beamsize_results
        self.magnet.scan(self.scan_values, self.measure_beamsize, beamsize_results)

        beam_sizes = []
        for result in beamsize_results:
            beam_sizes.append(result.rms_sizes * 1e-6)  # beam sizes in meters

        return

    def measure_beamsize(self, beamsize_results):
        """
        Take measurement from measurement device,
        and store results in `self._info`
        """
        time.sleep(self.wait_time)

        result = self.beamsize_measurement.measure()
        beamsize_results.append(result)

    def calculate_emittance(self):
        """

        Calculate the emittance from the measured beam sizes and quadrupole strengths.

        Returns:
        -------
        result : EmittanceMeasurementResult
            Object containing the results of the emittance measurement

        """

        # extract beam sizes from info
        beam_sizes = self._get_beamsizes()

        # get scan values and extend for each direction
        scan_values = np.tile(np.array(self.scan_values), (2, 1))

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
                    [
                        self.design_twiss["beta_x"],
                        self.design_twiss["alpha_x"],
                    ],
                    [
                        self.design_twiss["beta_y"],
                        self.design_twiss["alpha_y"],
                    ],
                ]
            )
        else:
            twiss_betas_alphas = None

        inputs = {
            "quad_vals": scan_values,
            "beamsizes": beam_sizes,
            "q_len": magnet_length,
            "rmat": self.rmat,
            "energy": self.energy,
            "twiss_design": (
                twiss_betas_alphas if twiss_betas_alphas is not None else None
            ),
        }

        # Call wrapper that takes quads in machine units and beamsize in meters
        results = compute_emit_bmag_quad_scan_machine_units(**inputs)
        results.update(
            {
                "metadata": self.model_dump()
                | {
                    "resolution": self.beamsize_measurement.beam_profile_device.resolution,
                    "image_data": {
                        str(sval): ele.model_dump()
                        for sval, ele in zip(self.scan_values, self._info)
                    },
                }
            }
        )

        # collect information into EmittanceMeasurementResult object
        return QuadScanEmittanceResult(**results)


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


def compute_emit_bmag_quad_scan(
    k: np.ndarray,
    beamsize_squared: np.ndarray,
    q_len: float,
    rmat: np.ndarray,
    twiss_design: np.ndarray = None,
    thin_lens: bool = False,
    maxiter: int = None,
):
    """
    Computes the emittance(s) corresponding to a set of quadrupole measurement scans
    using nonlinear fitting of beam matrix parameters to guarantee physically valid results.

    Parameters
    ----------
    k : numpy.ndarray
        Array of shape (n_steps_quad_scan,) or (batchshape x n_steps_quad_scan)
        representing the measurement quad geometric focusing strengths in [m^-2]
        used in the emittance scan(s).

    beamsize_squared : numpy.ndarray
        Array of shape (batchshape x n_steps_quad_scan), representing the mean-square
        beamsize outputs in [mm^2] of the emittance scan(s) with inputs given by k.

    q_len : float
        The (longitudinal) quadrupole length or "thickness" in [m].

    rmat : numpy.ndarray
        Array of shape (2x2) or (batchshape x 2 x 2) containing the 2x2 R matrices
        describing the transport from the end of the measurement quad to the observation screen.

    twiss_design : numpy.ndarray, optional
        Array of shape (batchshape x 2) designating the design (beta, alpha)
        twiss parameters at the screen.

    thin_lens : bool, optional
        Specifies whether or not to use thin lens approximation for measurement quad.

    maxiter : int, optional
        Maximum number of iterations to perform in nonlinear fitting (minimization algorithm).

    Returns
    -------
    dict
        Dictionary containing the following keys:
        - 'emittance': numpy.ndarray of shape (batchshape x 1) containing the geometric emittance
          fit results for each scan in mm-mrad.
        - 'bmag': numpy.ndarray of shape (batchshape x n_steps) containing the bmag corresponding
          to each point in each scan.
        - 'beam_matrix': numpy.ndarray of shape (batchshape x 3) containing [sig11, sig12, sig22]
          where sig11, sig12, sig22 are the reconstructed beam matrix parameters at the entrance
          of the measurement quad.
        - 'twiss_at_screen': numpy.ndarray of shape (batchshape x nsteps x 3) containing the
          reconstructed twiss parameters at the measurement screen for each step in each quad scan.
    """
    # calculate and add the measurement quad transport to the rmats
    quad_rmat = build_quad_rmat(
        k, q_len, thin_lens=thin_lens
    )  # result shape (batchshape x nsteps x 2 x 2)
    total_rmat = np.expand_dims(rmat, -3) @ quad_rmat
    # result shape (batchshape x nsteps x 2 x 2)

    # reshape inputs
    beamsize_squared = np.expand_dims(beamsize_squared, -1)
    twiss_design = (
        np.expand_dims(twiss_design, -2) if twiss_design is not None else None
    )

    # compute emittance
    rv = compute_emit_bmag(beamsize_squared, total_rmat, twiss_design, maxiter)

    return rv


def preprocess_inputs(quad_vals: list, beamsizes: list, energy: float, q_len: float):
    """
    Preprocesses the inputs for analyze_quad_scan.

    Parameters
    ----------
    quad_vals : list
        A list of two arrays containing the quadrupole values in kG for x and y respectively.
    beamsizes : dict
        A list of two arrays containing the beam sizes in meters for x and y respectively.
    energy : float
        The energy of the beam in eV.
    q_len : float
        The effective length of the quadrupole in meters.

    Returns
    -------
    tuple
        A tuple containing the list of kmod values and the list of beam sizes squared.
    """
    kmod_list = []
    beamsizes_squared_list = []

    for i in range(2):
        # Get rid of nans
        idx = ~np.isnan(beamsizes[i])
        q = quad_vals[i][idx]
        b = beamsizes[i][idx]

        # Beamsizes to mm squared
        beamsizes_squared_list.append((b * 1e3) ** 2)

        # Quad values to kmod
        kmod = bdes_to_kmod(energy, q_len, q)

        # Negate for y
        if i == 1:
            kmod = -1 * kmod

        kmod_list.append(kmod)

    return kmod_list, beamsizes_squared_list


def compute_emit_bmag_quad_scan_machine_units(
    quad_vals: list,
    beamsizes: list,
    q_len: float,
    rmat: np.ndarray,
    energy: float,
    twiss_design: np.ndarray,
    thin_lens: bool = False,
    maxiter: int = None,
):
    """
    Wrapper for analyze_quad_scan that takes quads in machine units and beamsize in meters.

    Parameters
    ----------
    quad_vals : list
        A list of two arrays containing the quadrupole values in kG for x and y respectively.
    beamsizes : list
        A list of two arrays containing the beam sizes in meters for x and y respectively.
    q_len : float
        The effective length of the quadrupole in meters.
    rmat : np.ndarray
        The R-matrix. Shape (2, 2, 2).
    energy : float
        The energy of the beam in eV.
    twiss_design : np.ndarray or None
        The design Twiss parameters. Shape (2, 2).
    thin_lens : bool, optional
        Whether to use the thin lens approximation. Default is False.
    maxiter : int, optional
        Maximum number of iterations for the optimization. Default is None.

    Returns
    -------
    dict
        The results of the emittance calculation.
    """  # Preprocessing data
    kmod_list, beamsizes_squared_list = preprocess_inputs(
        quad_vals, beamsizes, energy, q_len
    )

    # Prepare outputs
    results = {
        "emittance": [],
        "twiss_at_screen": [],
        "beam_matrix": [],
        "bmag": [] if twiss_design is not None else None,
        "quadrupole_focusing_strengths": [],
        "quadrupole_pv_values": [],
        "rms_beamsizes": [],
    }

    # Then call analyze_quad_scan
    # fit scans independently for x/y
    # only keep data that has non-nan beam sizes -- independent for x/y
    for i in range(2):
        result = compute_emit_bmag_quad_scan(
            k=kmod_list[i],
            beamsize_squared=beamsizes_squared_list[i],
            q_len=q_len,
            rmat=rmat[i],
            twiss_design=(twiss_design[i] if twiss_design is not None else None),
            thin_lens=thin_lens,
            maxiter=maxiter,
        )

        result.update({"quadrupole_focusing_strengths": kmod_list[i]})
        result.update({"quadrupole_pv_values": quad_vals[i][~np.isnan(beamsizes[i])]})

        # add results to dict object
        for name, value in result.items():
            if name == "bmag" and value is None:
                continue
            else:  # beam matrix and emittance get appended
                results[name].append(value)

        results["rms_beamsizes"].append(beamsizes[i][~np.isnan(beamsizes[i])])

    return results
