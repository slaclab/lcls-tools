from typing import (
    Any,
    Dict,
    Optional,
    Union,
)

from lcls_tools.common.devices.magnet import (
    Magnet,
    MagnetCollection,
)

from lcls_tools.common.devices.screen import (
    Screen,
    ScreenCollection,
)

from lcls_tools.common.devices.wire import (
    Wire,
    WireCollection,
)
from lcls_tools.common.devices.bpm import (
    BPM,
    BPMCollection,
)
from lcls_tools.common.devices.lblm import (
    LBLM,
    LBLMCollection,
)

from pydantic import SerializeAsAny, Field, field_validator

import lcls_tools


class Area(lcls_tools.common.BaseModel):
    """This class provides access to collections of hardware components
    in a given machine area of LCLS/LCLS-II (for example: BC1, or BC2).
    The information for each collection is provided in YAML configuration
    files, where the filename is the machine area.

    :cvar magnet_collection: The MagnetCollection for this area
    :cvar screen_collection: The ScreenCollection for this area
    """

    name: str = None
    magnet_collection: Optional[
        Union[
            SerializeAsAny[MagnetCollection],
            None,
        ]
    ] = Field(
        alias="magnets",
        default=None,
    )
    screen_collection: Optional[
        Union[
            SerializeAsAny[ScreenCollection],
            None,
        ]
    ] = Field(
        alias="screens",
        default=None,
    )
    wire_collection: Optional[
        Union[
            SerializeAsAny[WireCollection],
            None,
        ]
    ] = Field(
        alias="wires",
        default=None,
    )
    bpm_collection: Optional[
        Union[
            SerializeAsAny[BPMCollection],
            None,
        ]
    ] = Field(
        alias="bpms",
        default=None,
    )
    lblm_collection: Optional[
        Union[
            SerializeAsAny[LBLMCollection],
            None,
        ]
    ] = Field(
        alias="lblms",
        default=None,
    )

    def __init__(
        self,
        name,
        *args,
        **kwargs,
    ):
        super(Area, self).__init__(
            name=name,
            *args,
            **kwargs,
        )

    @field_validator(
        "magnet_collection",
        mode="before",
    )
    def validate_magnets(cls, v: Dict[str, Any]):
        if v:
            # Unpack the magnet data from yaml into MagnetCollection
            # before creating the magnet_collection
            return MagnetCollection(**{"magnets": {**v}})

    @field_validator(
        "screen_collection",
        mode="before",
    )
    def validate_screens(cls, v: Dict[str, Any]):
        if v:
            # Unpack the screens data from yaml into ScreenCollection
            return ScreenCollection(**{"screens": {**v}})

    @field_validator(
        "wire_collection",
        mode="before",
    )
    def validate_wires(cls, v: Dict[str, Any]):
        if v:
            # Unpack the wires data from yaml into WireCollection
            return WireCollection(**{"wires": {**v}})

    @field_validator(
        "bpm_collection",
        mode="before",
    )
    def validate_bpms(cls, v: Dict[str, Any]):
        if v:
            # Unpack the bpms data from yaml into BPMCollection
            return BPMCollection(**{"bpms": {**v}})

    @field_validator(
        "lblm_collection",
        mode="before",
    )
    def validate_lblms(cls, v: Dict[str, Any]):
        if v:
            # Unpack the lblms data from yaml into LBLMCollection
            return LBLMCollection(**{"lblms": {**v}})

    @property
    def magnets(
        self,
    ) -> Union[
        Dict[str, Magnet],
        None,
    ]:
        """
        A Dict[str, Magnet] for this area, where the dict keys are magnet names.
        If no magnets exist for this area, this property is None.
        """
        if self.magnet_collection:
            return self.magnet_collection.magnets
        else:
            print("Area does not contain magnets.")
            return None

    @property
    def screens(
        self,
    ) -> Union[
        Dict[str, Screen],
        None,
    ]:
        """
        A Dict[str, Screen] for this area, where the dict keys are screen names
        If no screens exist for this area, this property is None.
        """
        if self.screen_collection:
            return self.screen_collection.screens
        else:
            print("Area does not contain screens.")
            return None

    @property
    def wires(
        self,
    ) -> Union[
        Dict[str, Wire],
        None,
    ]:
        """
        A Dict[str, Wire] for this area, where the dict keys are wire names
        If no wires exist for this area, this property is None
        """
        if self.wire_collection:
            return self.wire_collection.wires
        else:
            print("Area does not contain wires.")
            return None

    @property
    def bpms(
        self,
    ) -> Union[
        Dict[str, BPM],
        None,
    ]:
        """
        A Dict[str, BPM] for this area, where the dict keys are bpm names
        If no bpms exist for this area, this property is None
        """
        if self.bpm_collection:
            return self.bpm_collection.bpms
        else:
            print("Area does not contain bpms.")
            return None

    @property
    def lblms(
        self,
    ) -> Union[
        Dict[str, LBLM],
        None,
    ]:
        """
        A Dict[str, LBLM] for this area, where the dict keys are lblm names
        If no lblms exist for this area, this property is None
        """
        if self.lblm_collection:
            return self.lblm_collection.lblms
        else:
            print("Area does not contain lblms.")
            return None

    def does_magnet_exist(
        self,
        magnet_name: str = None,
    ) -> bool:
        return magnet_name in self.magnets

    def does_screen_exist(
        self,
        screen_name: str = None,
    ) -> bool:
        return screen_name in self.screens

    def does_wire_exist(
        self,
        wire_name: str = None,
    ) -> bool:
        return screen_name in self.wires

    def does_bpm_exist(
        self,
        bpm_name: str = None,
    ) -> bool:
        return bpm_name in self.bpms

    def does_lblm_exist(
        self,
        lblm_name: str = None,
    ) -> bool:
        return lblm_name in self.lblms
