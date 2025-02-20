from pydantic import BaseModel, ConfigDict


class LCLSToolsBaseModel(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True, extra="forbid")
