from typing import (
    Any,
    Dict,
    Optional,
    Union,
)

from lcls_tools.common.devices.magnet import (
    MagnetCollection,
)

from lcls_tools.common.devices.screen import (
    ScreenCollection,
)

from pydantic import BaseModel, SerializeAsAny, field_validator


class Area(BaseModel):
    magnets: Optional[Union[SerializeAsAny[MagnetCollection], None]] = None
    screens: Optional[Union[SerializeAsAny[ScreenCollection], None]] = None

    @field_validator("magnets", mode="before")
    def validate_magnet_collection(cls, v: Dict[str, Any]):
        device_data = {}
        device_data["devices"] = v
        return MagnetCollection(**device_data)

    @field_validator("screens", mode="before")
    def validate_screen_collection(cls, v: Dict[str, Any]):
        device_data = {}
        device_data["devices"] = v
        return ScreenCollection(**device_data)

    def __init__(self, *args, **kwargs):
        super(Area, self).__init__(*args, **kwargs)
