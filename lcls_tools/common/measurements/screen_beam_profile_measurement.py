from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.image_processing.image_processing import ImageProcessor
from lcls_tools.common.data_analysis.projection_fit.projection_fit import ProjectionFit
from lcls_tools.common.measurements.measurement import Measurement
import numpy as np


class ScreenBeamProfileMeasurement(Measurement):
    """
    ScreenBeamProfileMeasurement class that allows for background subtraction and roi cropping
    ------------------------
    Arguments:
    name: str (name of measurement default is beam_profile),
    device: Screen (device that will be performing the measurement),
    image_processor: ImageProcessor ()
    fitting_tool: ProjectionFit ()
    fit_profile: bool = True ()
    ------------------------
    Methods:
    measure:
    single_measure:
    """


    name: str = "beam_profile"
    device: Screen
    image_processor: ImageProcessor
    fitting_tool: ProjectionFit
    fit_profile: bool = True
    # charge_window: Optional[ChargeWindow] = None

    def measure(self, n_shots: int = 1) -> dict:
        images = []
        while len(images) < n_shots:
            measurement = self.single_measure()
            if len(measurement):
                images += [measurement]
        # fit profile if requested
        results = {"images": images}
        if self.fit_profile:
            final_results = []
            for i, ele in enumerate(images):
                # concat dictionaries and store as list element, loop over all images
                temp = {}
                temp["raw_image"] = ele["raw_image"]
                temp["processed_image"] = ele["processed_image"]

                projection_x = np.array(np.sum(ele["processed_image"], axis=0))
                projection_y = np.array(np.sum(ele["processed_image"], axis=1))

                for key, param in self.fitting_tool.fit_projection(
                    projection_x).items():
                    key_x = key + "_x"
                    temp[key_x] = param

                for key, param in self.fitting_tool.fit_projection(
                    projection_y).items():
                    key_y = key + "_y"
                    temp[key_y] = param
                final_results += [temp]

            # what should I do with results now?
            results["fits"] = final_results

        # no attribute dump controller
        if self.save_data:
            pass
            # self.dump_controller.dump_data_to_file(final_results, self)

        return final_results

    def single_measure(self) -> dict:
        # measure profiles
        # get raw data
        raw_image = self.device.image
        # get ICT measurements and return None if not in window
        # if self.charge_window is not None:
        # if not self.charge_window.in_window():
        # return {}
        processed_image = self.image_processor.process(raw_image)
        return {"raw_image": raw_image, "processed_image": processed_image}
