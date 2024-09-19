from datetime import datetime
from pydantic import (
    BaseModel,
    # PositiveFloat,
    SerializeAsAny,
    field_validator,
    conint,
    ValidationError,
)
from typing import (
    Dict,
    List,
    Optional,
    Union,
)
from lcls_tools.common.devices.device import (
    Device,
    ControlInformation,
    Metadata,
    PVSet,
)
from epics import PV
import edef

EPICS_ERROR_MESSAGE = "Unable to connect to EPICS."


class BooleanModel(BaseModel):
    value: bool


class IntegerModel(BaseModel):
    value: conint(strict=True)


class LBLMPVSet(PVSet):
    # fast: PV
    gated_integral: PV
    i0_loss: PV

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @field_validator("*", mode="before")
    def validate_pv_fields(cls, v: str) -> PV:
        return PV(v)


class LBLMControlInformation(ControlInformation):
    PVs: SerializeAsAny[LBLMPVSet]
    _ctrl_options: SerializeAsAny[Optional[Dict[str, int]]] = dict()

    def __init__(self, *args, **kwargs):
        super(LBLMControlInformation, self).__init__(*args, **kwargs)
        # Get possible options for LBLM, empty dict by default.
    #     options = self.PVs.position.get_ctrlvars(timeout=1)
    #     if "enum_strs" in options:
    #         [
    #             self._ctrl_options.update({option: i})
    #             for i, option in enumerate(options["enum_strs"])
    #         ]

    # @property
    # def ctrl_options(self):
    #     return self._ctrl_options


class LBLMMetadata(Metadata):
    # material: Optional[str] = None
    # sum_l: Optional[PositiveFloat] = None
    # TODO: Add LBLM and BPM infomration here?
    # TODO: Add info on locations for X, Y, U wires

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class LBLM(Device):
    controls_information: SerializeAsAny[LBLMControlInformation]
    metadata: SerializeAsAny[LBLMMetadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    # @property
    # def fast(self):
    #     """get fast data"""
    #     return "fast"

    @property
    def i0_loss(self):
        """get i0 loss data"""
        return self.controls_information.PVs.i0_loss.get()

    def gated_integral(self):
        """get gated integral data"""
        print('gated integral')
        return self.controls_information.PVs.gated_integral.get()


class LBLMCollection(BaseModel):
    lblms: Dict[str, SerializeAsAny[LBLM]]

    @field_validator("lblms", mode="before")
    def validate_lblms(cls, v) -> Dict[str, LBLM]:
        for name, lblm in v.items():
            lblm = dict(lblm)
            # Set name field for LBLM
            lblm.update({"name": name})
            v.update({name: lblm})
        return v

    # TODO: can the next two functions get moved out?
    def seconds_since(self, time_to_check: datetime) -> int:
        if not isinstance(time_to_check, datetime):
            raise TypeError("Please provide a datetime object for comparison.")
        return (datetime.now() - time_to_check).seconds

    def _make_lblm_names_list_from_args(
        self, args: Union[str, List[str], None]
    ) -> List[str]:
        lblm_names = args
        if lblm_names:
            if isinstance(lblm_names, str):
                lblm_names = [args]
        else:
            lblm_names = list(self.lblms.keys())
        return lblm_names
