import time
import enum
from typing import Any, List, Literal, Optional
import warnings

import numpy as np
from numpy import ndarray
from pydantic import (
    ConfigDict,
    Field,
    SerializeAsAny,
    field_validator,
    PositiveFloat,
)

from lcls_tools.common.data.emittance import compute_emit_bmag
from lcls_tools.common.data.model_general_calcs import quad_scan_optics
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
    quad_to_diagnostic_rmat: ndarray, optional
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
    beamsize_measurement: BeamProfileMeasurement
    _info: Optional[list] = []

    quad_to_diagnostic_rmat: Optional[ndarray] = None
    design_twiss: Optional[dict] = None  # design twiss values
    physics_model: Literal["BMAD", "BLEM", "Lucretia"] = "BMAD"

    wait_time: PositiveFloat = 1.0

    name: str = "quad_scan_emittance"
    model_config = ConfigDict(arbitrary_types_allowed=True)

    @field_validator("quad_to_diagnostic_rmat")
    def validate_rmat(cls, v, info):
        assert v.shape == (2, 2, 2)
        return v

    @field_validator("magnet")
    def validate_magnet(cls, v, info):
        # extract beam sizes from info
        if v.metadata.l_eff is None:
            raise ValueError(
                "magnet length needs to be specified for magnet "
                f"{v.name} to be used in emittance measurement"
            )
        return v

    def measure(self):
        """
        Conduct quadrupole scan to measure the beam phase space.

        Returns:
        -------
        result : EmittanceMeasurementResult
            Object containing the results of the emittance measurement
        """

        # clear previous measurement info
        self._info = []

        # scan magnet strength and measure beamsize
        self.perform_beamsize_measurements()

        # calculate emittance from the measured beam sizes and quadrupole strengths
        return self.calculate_emittance()

    def calculate_emittance(self):
        """

        Calculate the emittance from the measured beam sizes and quadrupole strengths.

        Returns:
        -------
        result : EmittanceMeasurementResult
            Object containing the results of the emittance measurement

        """

        # organize data into arrays for use in `compute_emit_bmag`
        twiss_design = self.get_design_twiss()

        results = {
            "emittance": [],
            "twiss_at_screen": [],
            "beam_matrix": [],
            "bmag": [] if twiss_design is not None else None,
            "quadrupole_focusing_strengths": [],
            "quadrupole_pv_values": [],
            "rms_beamsizes": [],
        }
        for dim in ["x", "y"]:
            # preprocess info for given dimension
            preprocessed_info = self.preprocess_info(self._info, dim)

            # create dict of arguments for compute_emit_bmag
            if twiss_design is not None:
                emit_kwargs = {
                    "twiss_design": twiss_design[dim],
                }
            else:
                emit_kwargs = {"twiss_design": None}

            emit_kwargs.update(
                {
                    "beamsize_squared": preprocessed_info["rms_beamsizes"] ** 2,
                    "rmat": preprocessed_info["rmats"],
                }
            )

            # compute emittance and bmag
            result = compute_emit_bmag(**emit_kwargs)

            # add scan values to result dict
            result.update(
                {"quadrupole_focusing_strengths": preprocessed_info["kmod_values"]}
            )
            result.update({"quadrupole_pv_values": preprocessed_info["bctrl_values"]})
            result.update(
                {"rms_beamsizes": preprocessed_info["rms_beamsizes"].squeeze() * 1e-3}
            )

            # add results to dict object
            for name, value in result.items():
                if name == "bmag" and value is None:
                    continue
                else:  # beam matrix and emittance get appended
                    results[name].append(value)

        results.update(
            {
                "metadata": self.model_dump()
                | {
                    "resolution": self.beamsize_measurement.beam_profile_device.resolution,
                    "image_data": {str(ele["bctrl"]): ele for ele in self._info},
                }
            }
        )

        # collect information into EmittanceMeasurementResult object
        return EmittanceMeasurementResult(**results)

    def perform_beamsize_measurements(self):
        """Perform the beamsize measurements using a basic quadrupole scan."""
        self.magnet.scan(scan_settings=self.scan_values, function=self.measure_beamsize)

    def get_design_twiss(self):
        """
        Get the design twiss parameters from the design_twiss attribute or meme if available.

        Returns:
        -------
        ndarray
            Array of shape (2, 2) containing the design twiss parameters
            (beta, alpha) for x and y.
        """
        # if design twiss not provided, try to get from meme
        # if still not available, return None
        if self.design_twiss is None:
            try:
                optics = quad_scan_optics(
                    self.magnet,
                    self.beamsize_measurement,
                    self.physics_model,
                )
                twiss = optics["design_twiss"]
            except Exception as e:
                warnings.warn(
                    "Design twiss parameters could not be "
                    "calculated using meme. Returning None."
                )
                twiss = None
        else:
            twiss = self.design_twiss

        # if a twiss dictionary was obtained, convert to array
        if twiss is not None:
            return {
                "x": np.array([twiss["beta_x"], twiss["alpha_x"]]),
                "y": np.array([twiss["beta_y"], twiss["alpha_y"]]),
            }
        else:
            return None

    def get_rmat(self) -> ndarray:
        """
        Get the transport matrix from the beginning of the quadrupole to the
        profile monitor/wire scanner.

        If quad_to_diagnostic_rmat is provided,
        use it, along with the magnet bctrl value
        to calculate the rmat.

        Returns:
        -------
        rmat : ndarray
            The x/y transport matrix from the beginning of the quadrupole to the
            profile monitor/wire scanner, shape 2 x 2 x 2.

        """

        if self.quad_to_diagnostic_rmat is None:
            optics = quad_scan_optics(
                self.magnet,
                self.beamsize_measurement,
                self.physics_model,
            )
            rmat = optics["rmat"]
            # pick out x and y rmats
            rmat = np.stack([rmat[0:2, 0:2], rmat[2:4, 2:4]])

        else:
            rmat = compute_full_rmat(
                self.quad_to_diagnostic_rmat,
                self.magnet,
                self.energy,
            )

        return rmat

    def measure_beamsize(self):
        """
        Take measurement from measurement device,
        and store results in `self._info`
        """
        time.sleep(self.wait_time)

        result = self.beamsize_measurement.measure()

        # get rmat for given measurement
        rmat = self.get_rmat()
        length = self.magnet.metadata.l_eff
        bctrl = self.magnet.bctrl
        kmod = bdes_to_kmod(e_tot=self.energy, effective_length=length, bdes=bctrl)
        info = {
            "kmod": kmod,
            "rmat": rmat,
            "result": result.model_dump(),
            "bctrl": self.magnet.bctrl,
        }

        self._info += [info]

    def preprocess_info(self, info, dim):
        """
        Preprocess the info list containing `n_steps` elements
        to extract beam sizes, quadrupole strengths, and transport matrices
        for a given dimension.

        Parameters
        ----------
        dim : str
            Dimension to extract beam sizes for, either 'x' or 'y'.

        Returns
        -------
        dict
            Dictionary containing the following keys:
            - 'rms_beamsizes': ndarray of shape (n_steps, 1) containing the
              mean squared beam sizes in mm squared.
            - 'scan_values': ndarray of shape (n_steps,) containing the quadrupole
              strength values in [m^-2].
            - 'rmats': ndarray of shape (n_steps, 2, 2) containing the transport matrices
              for each step in the scan.
        """
        beam_sizes = []
        kmod_values = []
        bctrl_values = []
        rmats = []

        dim_index = 0 if dim == "x" else 1

        # extract mean beam sizes and scan values - skip nans
        for result in info:
            rms_size = result["result"]["rms_sizes"][dim_index]
            if np.isnan(rms_size):
                continue
            beam_sizes.append(rms_size * 1e-3)  # convert to mm
            kmod_values.append(result["kmod"])
            bctrl_values.append(result["bctrl"])
            rmats.append(result["rmat"][dim_index])

        rms_beamsizes = np.array(beam_sizes).reshape(-1, 1)
        bctrl_values = np.array(bctrl_values)
        rmats = np.array(rmats)

        # if dim == 'y', negate scan values
        if dim == "y":
            kmod_values = -1 * kmod_values

        return {
            "rms_beamsizes": rms_beamsizes,
            "bctrl_values": bctrl_values,
            "rmats": rmats,
            "kmod_values": kmod_values,
        }


class MultiDeviceEmittance(Measurement):
    name: str = "multi_device_emittance"

    def measure(self):
        raise NotImplementedError("Multi-device emittance not yet implemented")


def compute_full_rmat(
    quad_to_diagnostic_rmat: ndarray,
    magnet: Magnet,
    energy: float,
):
    """
    Compute the full transport matrix from the beginning of the quadrupole to the
    profile monitor/wire scanner.

    Parameters
    ----------
    quad_to_diagnostic_rmat : ndarray
        Transport matricies for the horizontal and vertical phase space from
        the end of the scanning magnet to the screen, array shape should be 2 x 2 x 2 (
        first element is the horizontal transport matrix, second is the vertical).
    magnet : Magnet
        The scanning magnet.
    energy : float
        The beam energy in GeV.

    Returns
    -------
    ndarray
        The x/y transport matrix from the beginning of the quadrupole to the
        profile monitor/wire scanner, shape 2 x 2 x 2.
    """
    integrated_gradient = magnet.bctrl
    length = magnet.metadata.l_eff
    kmod = bdes_to_kmod(e_tot=energy, effective_length=length, bdes=integrated_gradient)
    quad_rmat_x = build_quad_rmat(kmod, length, thin_lens=False)
    quad_rmat_y = build_quad_rmat(-kmod, length, thin_lens=False)
    quad_rmat = np.stack([quad_rmat_x, quad_rmat_y])
    rmat = quad_to_diagnostic_rmat @ quad_rmat

    return rmat
