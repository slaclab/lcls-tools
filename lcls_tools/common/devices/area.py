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
