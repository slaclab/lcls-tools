from pydantic import BaseModel, ConfigDict


class LCLSBaseModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
