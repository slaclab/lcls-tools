from typing import Any
from typing import Optional

from lcls_tools.common.devices.wire import Wire
from lcls_tools.common.devices.reader import create_lblm
from lcls_tools.common.data.fit.projection import ProjectionFit
from lcls_tools.common.measurements.measurement import Measurement
import time
import edef
import os
import lcls_tools
from pydantic import (
    ConfigDict,
    SerializeAsAny,
)
from lcls_tools.common.measurements.utils import NDArrayAnnotatedType
from lcls_tools.common.measurements.tmit_loss import TMITLoss
import numpy as np


class WireBeamProfileMeasurementResult(lcls_tools.common.BaseModel):
    position_data: NDArrayAnnotatedType
    detector_data: NDArrayAnnotatedType
    rms_sizes: Optional[NDArrayAnnotatedType] = None
    centroids: Optional[NDArrayAnnotatedType] = None
    metadata: SerializeAsAny[Any]

    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")


class WireBeamProfileMeasurement(Measurement):
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "beam_profile"
    device: Wire
    beampath: str
    beam_fit: ProjectionFit
    fit_profile: bool = True

    def measure(self, beampath, my_wire) -> dict:
        # """
        # Perform a wire scan measurement.

        # Parameters:
        # - beam_path (str): The selected beam path determines which timing
        #   buffer to reserve.
        # - my_wire (Wire): An lcls-tools wire object.

        # Returns:
        # dict: A dictionary containing the measured bunch charge values and
        # additional statistics if multiple shots are taken.

        # If n_shots is 1, the function returns a dictionary with the key
        # "bunch_charge_nC" and the corresponding single measurement value.

        # If n_shots is greater than 1, the function performs multiple
        # measurements with the specified wait time and returns a dictionary
        # with the key "bunch_charge_nC"  containing a list of measured
        # values. Additionally, statistical information (mean, standard
        # deviation, etc.) is included in the dictionary.

        # """

        devices = self.create_device_dictionary(my_wire)
        my_buffer = self.reserve_buffer(beampath)
        self.scan_with_wire(my_wire, my_buffer)
        data = self.get_buffer_data(my_wire, devices, beampath, my_buffer)
        position_data, detector_data = self.split_detector_data(my_wire, data)
        fit_result = self.fit_detector_data(detector_data)
        return WireBeamProfileMeasurementResult(
            position_data=position_data,
            detector_data=detector_data,
            fit_result=fit_result,
            metadata=self.model_dump()
        )

    def create_device_dictionary(self, my_wire):
        devices = {f"{my_wire.name}": my_wire}
        devices.update({lblm: create_lblm(area=f"{my_wire.area}", name=lblm)
                        for lblm in my_wire.metadata.lblms})
        return devices

    def reserve_buffer(self, beampath):
        user = os.getlogin()
        if 'SC' in beampath:
            my_buffer = edef.BSABuffer("LCLS Tools Wire Scan", user=user)
            return my_buffer
        elif 'CU' in beampath:
            my_buffer = edef.EventDefinition("LCLS Tools Wire Scan", user=user)
            return my_buffer
        else:
            raise BufferError

    def scan_with_wire(self, my_wire, my_buffer):
        my_buffer.start()

        # Wait for buffer to set to 'Not Ready' before moving wire
        time.sleep(0.1)

        # Start wire scan
        my_wire.start_scan()

        # Wait briefly before checking buffer 'ready'
        time.sleep(0.1)

    def get_buffer_data(self, my_wire, devices, beampath, my_buffer):
        data = {}
        # Wait for buffer 'ready'
        while not my_buffer.is_acquisition_complete():
            time.sleep(0.1)

        # Get buffer data and put into results dictionary
        data[f"{my_wire.name}"] = my_wire.position_buffer(my_buffer)
        if 'SC' in beampath:
            data.update({lblm: devices[lblm].fast_buffer(my_buffer) for lblm
                         in my_wire.metadata.lblms})
        elif 'CU' in beampath:
            data.update({lblm: devices[lblm].qdcraw_buffer(my_buffer) for lblm
                         in my_wire.metadata.lblms})

        # TODO: Insert TMIT Loss here?
        tmitloss_areas = ['HTR', 'DIAG0', 'COL1', 'EMIT2', 'BYP',
                          'SPD', 'LTUH', 'LTUS']
        if my_wire.area in tmitloss_areas:
            tl = TMITLoss(my_buffer)
            data['TMITLOSS'] = tl.measure()

        # Release EDEF/BSA
        my_buffer.release()

        # Return dictionary of Wire position, LBLM waveforms, BPM waveforms
        return data

    def split_detector_data(self, my_wire, data):
        # Get wire data to detemine plane indices
        position_data = data[f"{my_wire.name}"]

        # Hold plane ranges
        ranges = {}

        # Hold sequential indices (avoid catching return wires)
        seq_idxs = {}

        for plane in ['x', 'y', 'u']:
            # Get range methods e.g. x_range()
            method_name = f"{plane}_range"
            ranges[plane] = getattr(my_wire, method_name)()

            # Get indices of when position is within a range
            idx = np.where((position_data >= ranges[plane][0]) &
                           (position_data <= ranges[plane][1]))[0]
            # Get only sequential indices to avoid picking up wire retraction
            # data, ex. [100, 101, 102] not [101, 102, 103, 304, 305, 306]
            seq_idxs[plane] = np.split(idx, np.where(np.diff(idx) != 1)[0] + 1)

        # Make dictionary to hold individual datasets by plane
        # Ultimately will be detector_data[<plane>][<device_name>]
        detector_data = {'x': {},
                         'y': {},
                         'u': {}}

        for key in data.keys():
            # key is the device name
            # Pull entire device dataset
            device_data = data[key]
            for plane in ['x', 'y', 'u']:
                # Separate out device data by plane
                idx = seq_idxs[plane]
                device_plane_data = device_data[idx]
                detector_data[plane][key] = device_plane_data

        return position_data, detector_data

    def fit_detector_data(self, detector_data):
        fit_result = {}

        for key in detector_data.keys():
            for plane in ['x', 'y', 'u']:
                fit_result[plane][key] = self.beam_fit.fit_projection(
                    detector_data[plane][key])
