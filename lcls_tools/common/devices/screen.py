import os
import os
import time
from abc import ABC, abstractmethod
from copy import copy
from typing import (
    Dict,
    Optional, Union, List,
)

import numpy as np
from epics import PV
from matplotlib import patches
from pydantic import (
    BaseModel,
    SerializeAsAny,
    field_validator, FilePath, PositiveFloat,
)

from lcls_tools.common.devices.device import (
    Device,
    ControlInformation,
    Metadata,
    PVSet,
)


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
    background_file: Optional[FilePath] = None
    roi: Optional[ROI] = None
    timeout_in_seconds: PositiveFloat = 10.0

    def get_raw_image(self) -> np.ndarray:
        """
        Get the current image from EPICS
        reshaped to the dimensions of
        the camera associated with this screen
        """
        return self.controls_information.PVs.image.get(as_numpy=True).reshape(
            self.n_rows, self.n_columns
        )

    def get_processed_image(self) -> np.ndarray:
        """ get a processed image from EPICS"""
        img = self.get_raw_image()

        # subtract background if available
        if self.background_image is not None:
            img = img - self.background_image
            img = np.where(img >= 0, img, 0)

        # crop image if specified
        if self.roi is not None:
            img = self.roi.crop_image(img)
        return img

    def measure_background(self, n_measurements: int = 5, file_location: str = None):
        loc = copy(self.save_image_location)
        file_location = file_location or loc

        filename = os.path.join(file_location, f"{self.name}_background.npy")
        # insert shutter
        old_shutter_state = copy(self.beam_shuttered)
        self.shutter_beam()
        time.sleep(1.0)

        images = []
        for i in range(n_measurements):
            images += [self.get_processed_image()]
            time.sleep(self.wait_time_in_seconds)

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
    def background_image(self) -> Union[np.ndarray, None]:
        if self.background_file is not None:
            return np.load(self.background_file)
        else:
            return None

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
