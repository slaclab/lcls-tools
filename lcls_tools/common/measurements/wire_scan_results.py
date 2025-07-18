from pydantic import SerializeAsAny, BaseModel, ConfigDict
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
from typing import Any, Optional, Dict, Tuple
from datetime import datetime

from lcls_tools.common.measurements.beam_profile import BeamProfileMeasurementResult


class DetectorFit(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    mean: float
    sigma: float
    amplitude: float
    offset: float
    curve: NDArrayAnnotatedType


class FitResult(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    mean: float
    sigma: float
    amplitude: float
    offset: float
    curve: NDArrayAnnotatedType


class MeasurementMetadata(BaseModel):
    wire_name: str
    area: str
    beampath: str
    detectors: list[str]
    default_detector: str
    scan_ranges: Dict[str, Tuple[int, int]]
    timestamp: datetime
    notes: Optional[str] = None


class DetectorMeasurement(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    values: NDArrayAnnotatedType
    units: str | None = None
    label: str | None = None


class ProfileMeasurement(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    positions: NDArrayAnnotatedType
    detectors: dict[str, DetectorMeasurement]
    profile_idxs: NDArrayAnnotatedType


class WireBeamProfileMeasurementResult(BeamProfileMeasurementResult):
    """
    Stores the results of a wire beam profile measurement.

    Attributes:
        model_config: Allows use of non-standard types
                      like NDArrayAnnotatedType.
        profiles (dict): Dictionary of ProfileMeasurement objects
                         that contains raw data organized by profile.
        raw_data (dict): Dictionary of device data as np.ndarrays.
                         Keys are device names.
        fit_result (dict): Nested dictionary of fit parameters by detector.
        rms_sizes (ndarray): Numpy array containing (x_rms, y_rms) of
                          default detector.
        metadata: Various data relevant to the wire scan measurement.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)
    profiles: Dict[str, ProfileMeasurement]
    raw_data: Dict[str, Any]
    fit_result: NDArrayAnnotatedType
    metadata: SerializeAsAny[Any]
