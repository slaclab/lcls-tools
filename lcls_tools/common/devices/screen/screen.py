import asyncio
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
            return self.controls_information.PVs.arraydata.get(as_numpy=True)
        else:
            return self.controls_information.PVs.image.get(as_numpy=True)

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
        stamp = datetime.datetime.now()
        filename = str(stamp) + "_tst" + extension
        path = str(os.path.join(self._root_hdf5_location, filename)).replace(":", "_")
        print("****", path)
        return path

    def save_images(
        self,
        num_to_capture: int = 1,
        async_save: bool = True,
        extra_metadata: Optional[Dict[str, Any]] = None,
        threaded=True,
    ):
        # if threaded:
        self._threaded_take_images(num_to_capture)
        # else:
        #     return asyncio.run(
        #         self._save_images(
        #             num_to_capture=num_to_capture,
        #             async_save=async_save,
        #             extra_metadata=extra_metadata,
        #         )
        #     )

    def _threaded_take_images(self, num_collect):
        self.saving_images = True
        filename = self._generate_new_filename()
        captures = []
        last_updated_at = self.image_timestamp
        while len(captures) != num_collect:
            print(f"collecting images: {len(captures)} / {num_collect}")
            capture = self.image
            # wait until we have new data,
            # async sleep so GUIs do not hang
            if self.image_timestamp != last_updated_at:
                print("NEW IMAGE!")
                last_updated_at = self.image_timestamp
                captures.append(capture)
        print("collection done, writing out.")
        self._write_image_to_hdf5(
            images=captures,
            filename=filename,
            extra_metadata=None,
        )
        self._last_save_filepath = filename
        self.saving_images = False
        print("save images finished.")

    async def _collect_images(self, num_to_collect):
        captures = []
        last_updated_at = self.image_timestamp
        while len(captures) != num_to_collect:
            # wait until we have new data,
            # async sleep so GUIs do not hang
            if self.image_timestamp == last_updated_at:
                print("*******")
                await asyncio.sleep(1)
            else:
                capture = self.image
                last_updated_at = self.image_timestamp
                captures.append(capture)
        return captures

    async def _save_images(
        self,
        num_to_capture: int = 1,
        async_save: bool = False,
        extra_metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Collects and saves images from the camera associated with the screen.
        Images are saved in a single HDF5 file, each Capture being one image.
        Metadata can be saved as part of the file by setting the metadata flag.
        The full path to the file is returned but can be retrieved as a memeber too.
        """
        filename = self._generate_new_filename()
        captures = await self._collect_images(num_to_capture)

        # All images captured, save out to hdf5
        if async_save:
            # capture written to file in co-routine
            # so we can take the next capture
            await self._async_write_image_to_hdf5(
                images=captures,
                filename=filename,
                extra_metadata=extra_metadata,
            )
        else:
            self._write_image_to_hdf5(
                images=captures,
                filename=filename,
                extra_metadata=extra_metadata,
            )
        self._last_save_filepath = filename
        self.saving_images = False
        return filename

    async def _async_write_image_to_hdf5(
        self,
        images: np.ndarray,
        filename: str,
        extra_metadata: Optional[Dict] = None,
    ):
        with h5py.File(filename, "a") as f:
            capture_num = 0
            for image in images:
                dset = f.create_dataset(name=str(capture_num), data=image, dtype="f")
                [dset.attrs.update({key: value}) for key, value in self.metadata]
                if extra_metadata:
                    # may need to check for duplicate keys here, don't want to overwrite class-metadata.
                    [
                        dset.attrs.update({key: value})
                        for key, value in extra_metadata.items()
                    ]
                capture_num += 1
        return

    def _write_image_to_hdf5(
        self,
        images: np.ndarray,
        filename: str,
        extra_metadata: Optional[Dict] = None,
    ):
        with h5py.File(filename, "a") as f:
            capture_num = 0
            for image in images:
                dset = f.create_dataset(name=str(capture_num), data=image, dtype="f")
                [dset.attrs.update({key: value}) for key, value in self.metadata]
                if extra_metadata:
                    # may need to check for duplicate keys here, don't want to overwrite class-metadata.
                    [
                        dset.attrs.update({key: value})
                        for key, value in extra_metadata.items()
                    ]
                capture_num += 1
        return


class ScreenCollection(BaseModel):
    screens: Dict[str, SerializeAsAny[Screen]]
