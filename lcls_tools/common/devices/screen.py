import datetime
import os
import time
from abc import ABC, abstractmethod
from copy import copy
from typing import (
    Any,
    Dict,
    Optional, Union, List,
)
from threading import Thread

from matplotlib import pyplot as plt, patches

from lcls_tools.common.data_analysis.fitting_tool import FittingTool
from lcls_tools.common.devices.device import (
    Device,
    ControlInformation,
    Metadata,
    PVSet,
)

from epics import PV
import h5py
from pydantic import (
    BaseModel,
    SerializeAsAny,
    field_validator, FilePath, DirectoryPath, PositiveFloat,
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
    shutter: PV

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str):
        """Convert each PV string from YAML into a PV object"""
        return PV(v)


class ROI(BaseModel, ABC):
    roi_type: str
    center: List[PositiveFloat]

    @abstractmethod
    def crop_image(self, img, **kwargs) -> np.ndarray:
        """ crop image using ROI"""
        pass

    @abstractmethod
    def get_patch(self):
        pass


class CircularROI(ROI):
    """
    Define a circular region of interest (ROI) for an image, cropping pixels outside a
    bounding box around the ROI and setting pixels outside the boundary to a fill
    value (usually zero).
    """
    roi_type = "circular"
    radius: PositiveFloat

    @property
    def bounding_box(self):
        return [self.center[0] - int(self.radius),
                self.center[1] - int(self.radius),
                self.radius * 2, self.radius * 2]

    def crop_image(self, img, **kwargs) -> np.ndarray:
        x_size, y_size = img.shape
        fill_value = kwargs.get("fill_value", 0.0)

        if self.xwidth > x_size or self.ywidth > y_size:
            raise ValueError(
                f"must specify ROI that is smaller than the image, "
                f"image size is {img.shape}"
            )

        bbox = self.bounding_box
        img = img[..., bbox[0]: bbox[0] + bbox[2], bbox[1]: bbox[1] + bbox[3]]

        # TODO: fill px values outside region with fill value

        return img

    def get_patch(self):
        return patches.Circle(
            tuple(self.center), self.radius, facecolor="none", edgecolor="r"
        )


class RectangularROI(BaseModel):
    """
    Define a circular region of interest (ROI) for an image, cropping pixels outside
    the ROI.
    """

    xwidth: int
    ywidth: int

    @property
    def bounding_box(self):
        return [self.center[0] - int(self.xwidth / 2),
                self.center[1] - int(self.ywidth / 2),
                self.xwidth, self.ywidth]

    def crop_image(self, img, **kwargs) -> np.ndarray:
        x_size, y_size = img.shape

        if self.xwidth > x_size or self.ywidth > y_size:
            raise ValueError(
                f"must specify ROI that is smaller than the image, "
                f"image size is {img.shape}"
            )

        bbox = self.bounding_box
        img = img[bbox[0]: bbox[0] + bbox[2], bbox[1]: bbox[1] + bbox[3]]

        return img

    def get_patch(self):
        return patches.Rectangle(
            *self.bounding_box, facecolor="none", edgecolor="r"
        )


class ScreenControlInformation(ControlInformation):
    PVs: SerializeAsAny[ScreenPVSet]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Screen(Device):
    controls_information: SerializeAsAny[ScreenControlInformation]
    metadata: SerializeAsAny[Metadata]
    saving_images: bool = False
    save_location: Union[DirectoryPath, None] = None
    background_file: Optional[FilePath] = None
    wait_time: PositiveFloat = 1.0

    roi: Optional[ROI] = None
    fitting_tool: Optional[FittingTool] = None

    _last_save_filepath: Optional[str] = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def raw_image(self) -> np.ndarray:
        """
        The current image from EPICS
        reshaped to the dimensions of
        the camera associated with this screen
        """
        return self.controls_information.PVs.image.get(as_numpy=True).reshape(
            self.n_rows, self.n_columns
        )

    @property
    def processed_image(self) -> np.ndarray:
        img = self.raw_image
        # subtract background
        img = img - self.background_image
        img = np.where(img >= 0, img, 0)

        # crop image if specified
        if self.roi is not None:
            img = self.roi.crop_image(img)
        return img

    def measure_images(
            self,
            num_to_capture: int = 1,
            extra_metadata: Optional[Dict[str, Any]] = None,
            threaded=False,
            timeout_in_seconds: int = 10,
            fit_images: bool = True
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
            images = self._take_images(
                num_collect=num_to_capture,
                extra_metadata=extra_metadata,
                timeout=timeout_in_seconds,
            )

            if fit_images:
                if self.fitting_tool is not None:
                    image_stats = self.fitting_tool.fit_images(images)

                else:
                    raise RuntimeError("fitting tool required to fit images")

                result = image_stats | self.metadata
                result = result | extra_metadata

                return images, result

            else:
                return images, {}

    def test_measurement(
            self,
            timeout_in_seconds: int = 10,
            fit_images: bool = True
    ):

        image, result = self.measure_images(
            fit_images=fit_images, timeout_in_seconds=timeout_in_seconds
        )

        # visualize result
        fig, ax = plt.subplots()
        c = ax.imshow(image, origin="lower")
        fig.colorbar(c)

        # visualize beam bounding box, ROI, etc.
        beam_bounding_box = self.fitting_tool.get_beam_bounding_box()
        beam_centroid = [result["Cx"], result["Cy"]]
        ax.plot(*beam_centroid, "+r")
        ax.plot(*self.roi.center, ".r")
        rect = patches.Rectangle(
            *beam_bounding_box, facecolor="none", edgecolor="r"
        )
        ax.add_patch(rect)
        roi_patch = self.roi.get_patch()
        ax.add_patch(roi_patch)

    def _take_images(
            self,
            num_collect: int = 1,
            extra_metadata: Optional[Dict[str, Any]] = None,
            timeout: int = 10,
    ):
        """
        Performs the work for collecting images.
        This procedure will collect all images and then save them all to file if
        specified by the `save_images` attribute.

        If, for any image, we cannot collect within the time provided as timeout,
        we will stop collecting and save out what was collected before the failure.
        """

        captures = []
        last_updated_at = self.image_timestamp
        acquisition_start = datetime.datetime.now()
        while len(captures) != num_collect:
            # check timeout condition
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

                # if we are collecting multiple images wait some amount of time
                if num_collect > 1:
                    time.sleep(self.wait_time)

                acquisition_start = datetime.datetime.now()

        # collect list of images into a np array
        captures = np.array(captures)
        if self.save_images:
            filename = self._generate_new_filename()
            self._write_images_to_hdf5(
                images=captures,
                filename=filename,
                extra_metadata=extra_metadata,
            )
            self._last_save_filepath = filename

        return captures

    def measure_background(self, n_measurements: int = 5, file_location: str = None):
        loc = copy(self.save_image_location)
        file_location = file_location or loc

        filename = os.path.join(file_location, f"{self.name}_background.npy")
        # insert shutter
        old_shutter_state = copy(self.beam_shuttered)
        self.shutter_beam()
        time.sleep(1.0)

        images = self._take_images(n_measurements)

        # restore shutter state
        if old_shutter_state:
            self.shutter_beam()
        else:
            self.unshutter_beam()

        # return average
        images = np.stack(images)
        mean = images.mean(axis=0)

        np.save(filename, mean)
        self.background_file = filename

        return mean

    @property
    def image_timestamp(self):
        """Get last timestamp for last PV activity"""
        return self.controls_information.PVs.image.timestamp

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
        """Location and filename for the last file saved by this screen (set in
        save_images())"""
        return self._last_save_filepath

    @property
    def beam_shuttered(self) -> bool:
        """ returns True if the laser/beam is shuttered"""
        return not self.controls_information.PVs.shutter.get()

    def shutter_beam(self):
        self.controls_information.PVs.shutter.put(0)

    def unshutter_beam(self):
        self.controls_information.PVs.shutter.put(1)

    def _inserted_check(self):
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

    def _write_images_to_hdf5(
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


class ScreenCollection(BaseModel):
    screens: Dict[str, SerializeAsAny[Screen]]

    @field_validator("screens", mode="before")
    def validate_screens(cls, v):
        """
        Add name field to data that will be passed to Screen class
        and then use that dictionary to create each Screen.
        """
        for name, screen in v.items():
            screen = dict(screen)
            screen.update({"name": name})
            v.update({name: screen})
        return v

    def set_hdf_save_location(self, location: str):
        """Sets the HDF5 save location all of the screens in the collection."""
        if not os.path.isdir(location):
            raise AttributeError(
                f"Could not set {location} HDF5 save location. Please provide an existing directory."
            )
        for _, screen in self.screens.items():
            screen.hdf_save_location = location
