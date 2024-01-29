from lcls_tools.common.devices.ict import ICT
from lcls_tools.common.measurements.measurement import Measurement


class BeamChargeMeasurement(Measurement):
    name = "beam_charge"
    ict_monitor: ICT

    def measure(self) -> dict:
        return {"bunch_charge_nC": self.ict_monitor.get_charge()}

