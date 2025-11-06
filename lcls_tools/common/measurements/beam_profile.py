from abc import abstractmethod
from typing import Any

from lcls_tools.common.devices.device import Device
from lcls_tools.common.measurements.measurement import Measurement
from pydantic import (
    ConfigDict,
    SerializeAsAny,
)
from typing import Optional

from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
import lcls_tools


class BeamProfileMeasurementResult(lcls_tools.common.BaseModel):
    """
    Class that contains the results of a beam profile measurement
    (for any set of axes)

    Attributes
    ----------
    rms_sizes : ndarray
        Numpy array of rms sizes of the beam in microns.
    centroids : ndarray
        Numpy array of centroids of the beam in microns.
    total_intensities : ndarray
        Numpy array of total intensities of the beam.
    metadata : Any
        Metadata information related to the measurement.

    """

    rms_sizes: Optional[NDArrayAnnotatedType] = None
    centroids: Optional[NDArrayAnnotatedType] = None
    total_intensities: Optional[NDArrayAnnotatedType] = None
    signal_to_noise_ratios: Optional[NDArrayAnnotatedType] = None
    metadata: SerializeAsAny[Any]

    model_config = ConfigDict(arbitrary_types_allowed=True)


class BeamProfileMeasurement(Measurement):
    """
    Class that allows for beam profile measurements and fitting
    (for any set of axes)
    ------------------------
    Arguments:
    name: str (name of measurement default is beam_profile),
    device: Device (device that will be performing the measurement),
    ------------------------
    Methods:
    measure: measures beam profile
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "beam_profile"
    beam_profile_device: Device

    @abstractmethod
    def measure(self) -> BeamProfileMeasurementResult:
        """
        Measure the beam profile and return a BeamProfileMeasurementResult
        """
        pass
