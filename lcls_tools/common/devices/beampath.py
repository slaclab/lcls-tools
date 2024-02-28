from typing import (
    Dict,
)

from lcls_tools.common.devices.area import (
    Area,
)


from pydantic import BaseModel, SerializeAsAny


class Beampath(BaseModel):
    areas: Dict[str, SerializeAsAny[Area]]

    def __init__(self, *args, **kwargs):
        super(Beampath, self).__init__(*args, **kwargs)
