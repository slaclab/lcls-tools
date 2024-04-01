import os
import time
from datetime import datetime
from threading import Thread
from typing import Optional, List, Dict, Any

import h5py
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from numpy import ndarray
from pydantic import (
    BaseModel,
    DirectoryPath, PositiveFloat,
)

from lcls_tools.common.controls.pyepics.utils import PV
from lcls_tools.common.data_analysis.fitting_tool import FittingTool
from lcls_tools.common.devices.screen import Screen


class ScreenProfileMeasurement(BaseModel):
    device: Screen
    fitting_tool: Optional[FittingTool] = None

    save_location: Optional[DirectoryPath] = None
    save_data: bool = True
    extra_pvs: List[PV] = []
    wait_time_in_seconds: PositiveFloat = 1.0
    condition_list: List = []

    def measure_profile(
            self, n_shots=1, use_conditions: bool = True
    ) -> [dict, ndarray]:
        images, scalar_measurements = self.acquire_images(
            n_shots, use_conditions=use_conditions
        )

        # collect results into a single dict using pandas
        if n_shots == 1:
            outputs = scalar_measurements[0]
        else:
            # collect results into lists
            outputs = pd.DataFrame(scalar_measurements).reset_index().to_dict(
                orient="list")
            outputs.pop("index")

        # add beam statistics to output
        if self.fitting_tool is not None:
            beam_statistics = self.fitting_tool.fit_images(images)
            for name, val in beam_statistics:
                outputs[name] = val

        # save data if requested, add filename to outputs
        if self.save_data:
            fname = self._generate_new_filename()
            self._write_data_to_hdf5(
                np.array(images), fname, outputs)
            outputs["save_filename"] = outputs

        return outputs, images

    def test_measurement(self):
        """test the beam profile measurement"""
        outputs, images = self.measure_profile(1, use_conditions=False)

        print(outputs)
        fig, ax = plt.subplots()
        c = ax.imshow(images[0], origin="lower")
        fig.colorbar(c)

        plt.show()

    def acquire_images(self, n_shots: int = 1, threaded=False, use_conditions=True):
        """
        Collect and saves images to HDF5.
        Option for threading which spawns a child process
        in a way that dependant GUIs/Code do not hang.
        The extra_metadata dictionary will be attached
        to the metadata for each image in HDF5 .

        """
        if threaded:
            work = Thread(
                target=self._take_images,
                args=[n_shots, use_conditions],
            )
            # normally we join after start, but that blocked the pyqt main thread
            # so we do not join here. If it breaks, look here first..
            work.start()
        else:
            return self._take_images(n_shots, use_conditions)

    def _take_images(self, n_shots: int = 1, use_conditions: bool = True):
        """
        Performs the work for collecting images and associated scalar data for a set
        number of shots. Conditions such as charge windowing are applied.

        """

        images = []
        scalar_measurements = []
        while len(images) < n_shots:
            time.sleep(self.wait_time_in_seconds)

            # get image and PV's at the same time
            img = self.device.get_processed_image()

            # get extra pv values
            result = {ele.pvname: ele.caget() for ele in self.extra_pvs}

            # check to make sure all measurement conditions are satisfied
            # if a condition is not satisfied then continue
            if use_conditions:
                for condition in self.condition_list:
                    is_satisfied = condition.evaluate()
                    result = result | condition.measurements()
                    if not is_satisfied:
                        continue

            # if all conditions are satisfied then add the image and extra pv data to
            # the list
            images += [img]
            scalar_measurements += [result]

        return images, scalar_measurements

    def _generate_new_filename(self, extension: Optional[str] = ".h5") -> str:
        """
        Make a new filename for the HDF5 image file
        Should be of the form: <save-location>/<timestamp>_<screen_name>.h5
        """
        stamp = datetime.now().isoformat()
        stamp_str = stamp.replace(".", "_").replace("-", "_").replace(":", "_")
        filename = stamp_str + "_" + self.name + extension
        path = str(os.path.join(self._root_hdf5_location, filename))
        return path

    def _write_data_to_hdf5(
            self,
            images: np.ndarray,
            filename: str,
            extra_metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Saves a set of images to the hdf_save_location with the filename provided.
        Any metadata provided as extra_metadata will be attached to each dataset in the HDF5 file.
        """
        with h5py.File(filename, "a") as f:
            capture_num = 0
            for image in images:
                # todo, check type-representation of images, are we sure they are unsigned-shorts??
                dset = f.create_dataset(
                    name=str(capture_num), data=image, dtype=np.ushort
                )
                [dset.attrs.update({key: value}) for key, value in self.metadata]
                if extra_metadata:
                    # dset.attrs acts as a dictionary here
                    # we update with original key if it isn't in our normal screen metadata
                    # otherwise, prepend user_ to the key to retain all information.
                    [
                        dset.attrs.update({key: value})
                        if key not in self.metadata
                        else dset.attrs.update({"user_" + key: value})
                        for key, value in extra_metadata.items()
                    ]

                capture_num += 1
        return
