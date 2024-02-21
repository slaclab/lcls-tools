import numpy as np
from pydantic import PositiveFloat

from lcls_tools.common.devices.ict import ICT
from lcls_tools.common.measurements.measurement import Measurement
import time

from lcls_tools.common.measurements.utils import calculate_statistics


class BeamChargeMeasurement(Measurement):
    name = "beam_charge"
    ict_monitor: ICT
    wait_time: PositiveFloat = 1.0

    def measure(self, n_shots: int = 1) -> dict:
        """
        Measure the bunch charge using an ICT monitor.

        Parameters:
        - n_shots (int, optional): The number of measurements to perform. Defaults to 1.

        Returns:
        dict: A dictionary containing the measured bunch charge values and additional
        statistics if multiple shots are taken.

        If n_shots is 1, the function returns a dictionary with the key "bunch_charge_nC"
        and the corresponding single measurement value.

        If n_shots is greater than 1, the function performs multiple measurements with
        the specified wait time and returns a dictionary with the key "bunch_charge_nC"
        containing a list of measured values. Additionally, statistical information
        (mean, standard deviation, etc.) is included in the dictionary.


        """
        if n_shots == 1:
            return {"bunch_charge_nC": self.ict_monitor.get_charge()}
        elif n_shots > 1:
            bunch_charges = []
            for i in range(n_shots):
                bunch_charges += [self.ict_monitor.get_charge()]
                time.sleep(self.wait_time)

            # add statistics to results
            results = {"bunch_charge_nC": bunch_charges}
            results = results | calculate_statistics(
                np.array(bunch_charges), "bunch_charge_nC"
            )

            return results
