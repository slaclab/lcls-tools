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

from pydantic import BaseModel, SerializeAsAny, Field, field_validator


class Area(BaseModel):
    """This class provides access to collections of hardware components
    in a given machine area of LCLS/LCLS-II (for example: BC1, or BC2).
    The information for each collection is provided in YAML configuration
    files, where the filename is the machine area.

    :cvar magnet_collection: The MagnetCollection for this area
    :cvar screen_collection: The ScreenCollection for this area
    """

    magnet_collection: Optional[Union[SerializeAsAny[MagnetCollection], None]] = None
    screen_collection: Optional[Union[SerializeAsAny[ScreenCollection], None]] = None

    @property
    def magnets(self) -> Union[Dict[str, Magnet], None]:
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
    def screens(self) -> Union[Dict[str, Screen], None]:
        """
        A Dict[str, Screen] for this area, where the dict keys are screen names
        If no screens exist for this area, this property is None.
        """
        if self.screen_collection:
            return self.screen_collection.screens
        else:
            print("Area does not contain screens.")
            return None

    @field_validator("magnet_collection", mode="before")
    def validate_magnets(cls, v: Dict[str, Any]):
        if v:
            return MagnetCollection(**{"magnets": {**v}})

    @field_validator("screen_collection", mode="before")
    def validate_screens(cls, v: Dict[str, Any]):
        if v:
            return ScreenCollection(**{"screens": {**v}})

    def __init__(self, *args, **kwargs):
        super(Area, self).__init__(*args, **kwargs)
