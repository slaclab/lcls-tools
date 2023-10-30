from pydantic import BaseModel, PositiveFloat
from typing import Dict, List, Optional

class ControlInformation(BaseModel):
    control_name : str
    PVs : Dict[str, str]
    ctrl_options: Dict[str, int]

class Metadata(BaseModel):
    area: str
    beam_path: Optional[List[str]]
    sum_l_meters: Optional[float]
    length: PositiveFloat
    b_tolerance: PositiveFloat

class Magnet(BaseModel):
    control_information: ControlInformation
    metadata: Metadata

class MagnetCollection(BaseModel):
    magnets: Dict[str, Magnet]

