import datetime
import os
from typing import (
    Any,
    Dict,
    Optional,
    Union,
)
from threading import Thread

from pydantic import (
    BaseModel,
    SerializeAsAny,
    field_validator,
)
from lcls_tools.common.devices.device import (
    Device,
    ControlInformation,
    Metadata,
    PVSet,
)
from epics import PV
import h5py
import numpy as np


class ScreenPVSet(PVSet):
    """
    The PV interface for screens is not uniform.
    We list the potential PVs below and only
    use the ones that are set to be PV-typed after
    initialisation.
    """

    arraydata: Optional[Union[PV, None]] = None
    arraysizex_rbv: Optional[Union[PV, None]] = None
    arraysizey_rbv: Optional[Union[PV, None]] = None
    image: Optional[Union[PV, None]] = None
    n_of_col: Optional[Union[PV, None]] = None
    n_of_row: Optional[Union[PV, None]] = None
    n_of_bits: PV
    resolution: PV

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str):
        if v:
            return PV(v)


class ScreenControlInformation(ControlInformation):
    PVs: SerializeAsAny[ScreenPVSet]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class Screen(Device):
    controls_information: SerializeAsAny[ScreenControlInformation]
    metadata: SerializeAsAny[Metadata]
    use_arraydata: Optional[bool] = False
    saving_images: Optional[bool] = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # check if we use :Image:ArrayData or :IMAGE for waveforms.
        self.use_arraydata = (self.controls_information.PVs.arraydata is not None) and (
            self.controls_information.PVs.arraydata.connected()
        )
        self._root_hdf5_location: Optional[str] = os.path.join(
            "/home/matt", "hdf5_test"
        )
        self._last_save_filepath: Optional[str] = ""
        self.saving_images = False

    @property
    def image(self):
        if self.use_arraydata:
            return self.controls_information.PVs.arraydata.get(as_numpy=True).reshape(
                self.n_rows, self.n_columns
            )
        else:
            return self.controls_information.PVs.image.get(as_numpy=True).reshape(
                self.n_rows, self.n_columns
            )

    @property
    def image_timestamp(self):
        """get last timestamp for last PV activity"""
        if self.use_arraydata:
            return self.controls_information.PVs.arraydata.timestamp
        else:
            return self.controls_information.PVs.image.timestamp

    @property
    def n_columns(self):
        if self.use_arraydata:
            return self.controls_information.PVs.arraysizey_rbv.get()
        else:
            return self.controls_information.PVs.n_of_col.get()

    @property
    def n_rows(self):
        if self.use_arraydata:
            return self.controls_information.PVs.arraysizex_rbv.get()
        else:
            return self.controls_information.PVs.n_of_row.get()

    @property
    def n_bits(self):
        return self.controls_information.PVs.n_of_bits.get()

    @property
    def resolution(self):
        return self.controls_information.PVs.resolution.get()

    @property
    def last_save_filepath(self):
        return self._last_save_filepath

    def _generate_new_filename(self, extension: Optional[str] = ".h5") -> str:
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
    ):
        if threaded:
            work = Thread(
                target=self._take_images,
                args=[
                    num_to_capture,
                    extra_metadata,
                ],
            )
            # normally we join after start, but that blocked the pyqt main thread
            # so we do not join here. If it breaks, look here first..
            work.start()
        else:
            self._take_images(
                num_collect=num_to_capture,
                extra_metadata=extra_metadata,
            )

    def _take_images(
        self, num_collect: int = 1, extra_metadata: Optional[Dict[str, Any]] = None
    ):
        self.saving_images = True
        filename = self._generate_new_filename()
        captures = []
        last_updated_at = self.image_timestamp
        while len(captures) != num_collect:
            if self.image_timestamp != last_updated_at:
                capture = self.image
                last_updated_at = self.image_timestamp
                captures.append(capture)
        self._write_image_to_hdf5(
            images=captures,
            filename=filename,
            extra_metadata=extra_metadata,
        )
        self._last_save_filepath = filename
        self.saving_images = False
        print("save images finished.")
        return

    def _write_image_to_hdf5(
        self,
        images: np.ndarray,
        filename: str,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ):
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
        for name, screen in v.items():
            screen = dict(screen)
            screen.update({"name": name})
            v.update({name: screen})
        return v
