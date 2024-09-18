import datetime
import os
from typing import (
    Any,
    Dict,
    Optional,
)
from threading import Thread

from lcls_tools.common.devices.device import (
    Device,
    ControlInformation,
    DeviceCollection,
    Metadata,
    PVSet,
)

from epics import PV
import h5py
from pydantic import (
    Field,
    SerializeAsAny,
    field_validator,
)
import numpy as np


class ScreenPVSet(PVSet):
    """
    The PV interface for screens is not uniform.
    We list the potential PVs below and only
    use the ones that are set to be PV-typed after
    initialisation.
    """

    image: PV
    n_col: PV
    n_row: PV
    n_bits: PV
    resolution: PV

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str):
        """Convert each PV string from YAML into a PV object"""
        return PV(v)


class ScreenControlInformation(ControlInformation):
    PVs: SerializeAsAny[ScreenPVSet]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Screen(Device):
    controls_information: SerializeAsAny[ScreenControlInformation]
    metadata: SerializeAsAny[Metadata]
    _saving_images: Optional[bool] = False
    _root_hdf5_location: Optional[str] = "."
    _last_save_filepath: Optional[str] = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def image(self) -> np.ndarray:
        """
        The current image from EPICS
        reshaped to the dimensions of
        the camera associated with this screen
        """
        return self.controls_information.PVs.image.get(as_numpy=True).reshape(
            self.n_rows, self.n_columns
        )

    @property
    def image_timestamp(self):
        """Get last timestamp for last PV activity"""
        return self.controls_information.PVs.image.timestamp

    @property
    def hdf_save_location(self) -> str:
        """The location where any HDF5 file for images is saved for this screen"""
        return self._root_hdf5_location

    @hdf_save_location.setter
    def hdf_save_location(self, path: str):
        """Set the save location of any HDF5 files for images of this screen"""
        if not os.path.isdir(path):
            raise AttributeError(
                f"Could not set {self.name} HDF5 save location. Please provide an existing directory."
            )
        self._root_hdf5_location = path

    @property
    def is_saving_images(self):
        return self._saving_images

    @property
    def n_columns(self):
        """The number of columns in the screen image"""
        return self.controls_information.PVs.n_col.get()

    @property
    def n_rows(self):
        """The number of rows in the screen image"""
        return self.controls_information.PVs.n_row.get()

    @property
    def n_bits(self):
        """The number of bits to represent each pixel in the image"""
        return self.controls_information.PVs.n_bits.get()

    @property
    def resolution(self):
        """The conversion factor of pixels to mm"""
        return self.controls_information.PVs.resolution.get()

    @property
    def last_save_filepath(self):
        """Location and filename for the last file saved by this screen (set in save_images())"""
        return self._last_save_filepath

    def _inserted_check():
        """Check if the screen is inserted"""
        return NotImplementedError

    def _generate_new_filename(self, extension: Optional[str] = ".h5") -> str:
        """
        Make a new filename for the HDF5 image file
        Should be of the form: <save-location>/<timestamp>_<screen_name>.h5
        """
        stamp = datetime.datetime.now().isoformat()
        stamp_str = stamp.replace(".", "_").replace("-", "_").replace(":", "_")
        filename = stamp_str + "_" + self.name + extension
        path = str(os.path.join(self._root_hdf5_location, filename))
        return path

    def save_images(
        self,
        num_to_capture: int = 1,
        extra_metadata: Optional[Dict[str, Any]] = None,
        threaded=True,
        timeout_in_seconds: int = 10,
    ):
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
                args=[
                    num_to_capture,
                    extra_metadata,
                    timeout_in_seconds,
                ],
            )
            # normally we join after start, but that blocked the pyqt main thread
            # so we do not join here. If it breaks, look here first..
            work.start()
        else:
            self._take_images(
                num_collect=num_to_capture,
                extra_metadata=extra_metadata,
                timeout=timeout_in_seconds,
            )

    def _take_images(
        self,
        num_collect: int = 1,
        extra_metadata: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = 10,
    ):
        """
        Performs the work for collecting images and saving to HDF5 file.
        This procedure will collect all images and then save them all to file.

        If, for any image, we cannot collect within the time provided as timeout,
        we will stop collecting and save out what was collected before the failure.
        """
        self._saving_images = True
        filename = self._generate_new_filename()
        captures = []
        last_updated_at = self.image_timestamp
        acquisition_start = datetime.datetime.now()
        while len(captures) != num_collect:
            if datetime.datetime.now() - acquisition_start > datetime.timedelta(
                seconds=timeout
            ):
                print(
                    "Could not save capture ",
                    len(captures) + 1,
                    " out of ",
                    num_collect,
                    " due to timeout. Exiting image collection for ",
                    self.name,
                    ". Saving out to HDF5 will happen now.",
                )
                break
            if self.image_timestamp != last_updated_at:
                capture = self.image
                last_updated_at = self.image_timestamp
                captures.append(capture)
                acquisition_start = datetime.datetime.now()
        self._write_image_to_hdf5(
            images=captures,
            filename=filename,
            extra_metadata=extra_metadata,
        )
        self._last_save_filepath = filename
        self._saving_images = False
        print("save images finished.")
        return

    def _write_image_to_hdf5(
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
                        (
                            dset.attrs.update({key: value})
                            if key not in self.metadata
                            else dset.attrs.update({"user_" + key: value})
                        )
                        for key, value in extra_metadata.items()
                    ]

                capture_num += 1
        return


class ScreenCollection(DeviceCollection):
    devices: Dict[str, SerializeAsAny[Screen]] = Field(alias="screens")

    def __init__(self, *args, **kwargs):
        super(ScreenCollection, self).__init__(*args, **kwargs)

    @property
    def screens(self) -> Dict[str, SerializeAsAny[Screen]]:
        return self.devices

    def set_hdf_save_location(self, location: str):
        """Sets the HDF5 save location all of the screens in the collection."""
        if not os.path.isdir(location):
            raise AttributeError(
                f"Could not set {location} HDF5 save location. Please provide an existing directory."
            )
        for _, screen in self.devices.items():
            screen.hdf_save_location = location
