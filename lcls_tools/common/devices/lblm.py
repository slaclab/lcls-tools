from datetime import datetime
from pydantic import (
    BaseModel,
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

EPICS_ERROR_MESSAGE = "Unable to connect to EPICS."


class BooleanModel(BaseModel):
    value: bool


class FloatModel(BaseModel):
    value: float


class IntegerModel(BaseModel):
    value: conint(strict=True)


class LBLMPVSet(PVSet):
    gated_integral: Optional[PV] = None
    i0_loss: Optional[PV] = None
    gain: Optional[PV] = None
    bypass: Optional[PV] = None

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


class LBLMMetadata(Metadata):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class LBLM(Device):
    controls_information: SerializeAsAny[LBLMControlInformation]
    metadata: SerializeAsAny[LBLMMetadata]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def fast_buffer(self, buffer):
        """Retrieve fast signal data from timing buffer"""
        # :FAST PV confusingly does not exist outside of buffer
        # get_data_buffer requires PV name as string, not EPICS PV object
        pv = f"{self.controls_information.control_name}:FAST"
        data = buffer.get_data_buffer(pv)
        if data is None:
            raise BufferError("No data in buffer or PV not found")
        return data

    @property
    def i0_loss(self):
        """Get I0 Loss value"""
        pv = self.controls_information.PVs.i0_loss
        if pv is None:
            raise AttributeError("I0_LOSS PV is not defined for this device")
        return pv.get()

    def i0_loss_buffer(self, buffer):
        """Retrieve I0 Loss data from timing buffer"""
        pv = self.controls_information.PVs.i0_loss
        if pv is None:
            raise AttributeError("I0_LOSS PV is not defined for this device")
        # get_data_buffer requires PV name as string, not EPICS PV object
        data = buffer.get_data_buffer(self.controls_information.PVs.i0_loss.pvname)
        if data is None:
            raise BufferError("No data in buffer or PV not found")
        return data

    @property
    def gated_integral(self):
        """Get Gated Integral value"""
        pv = self.controls_information.PVs.gated_integral
        if pv is None:
            raise AttributeError("GATED_INTEGRAL PV is not defined for this device")
        return pv.get()

    def gated_integral_buffer(self, buffer):
        """Get Gated Integral data from timing buffer"""
        pv = self.controls_information.PVs.gated_integral
        if pv is None:
            raise BufferError("GATED_INTEGRAL PV is not defined for this device")
        # get_data_buffer requires PV name as string, not EPICS PV object
        data = buffer.get_data_buffer(
            self.controls_information.PVs.gated_integral.pvname
        )
        if data is None:
            raise BufferError("No data in buffer or PV not found")
        return data

    @property
    def gain(self):
        """Get gain value"""
        pv = self.controls_information.PVs.gain
        if pv is None:
            raise AttributeError("GAIN PV is not defined for this device")
        return pv.get()

    @gain.setter
    def gain(self, val: float) -> None:
        try:
            FloatModel(value=val)
            self.controls_information.PVs.gain.put(value=val)
        except ValidationError as e:
            print("Gain must be a float:", e)

    @property
    def bypass(self):
        """Get bypass state"""
        pv = self.controls_information.PVs.bypass
        if pv is None:
            raise AttributeError("BYPASS PV is not defined for this device")
        return pv.get()

    @bypass.setter
    def bypass(self, val: bool) -> None:
        try:
            BooleanModel(value=val)
            self.controls_information.PVs.bypass.put(value=val)
        except ValidationError as e:
            print("Bypass must be a boolean:", e)


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
