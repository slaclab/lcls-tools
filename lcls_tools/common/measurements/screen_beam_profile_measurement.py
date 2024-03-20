from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.image_processing.image_processing import ImageProcessor
from lcls_tools.common.data_analysis.projection_fit.projection_fit import ProjectionFit
from lcls_tools.common.measurements.measurement import Measurement
import numpy as np
class ScreenBeamProfileMeasurement(Measurement):
    name: str = "beam_profile"
    device: Screen
    image_processor: ImageProcessor
    fitting_tool: ProjectionFit
    fit_profile: bool = True
    # charge_window: Optional[ChargeWindow] = None

    def measure(self,n_shots:int = 1 ) -> dict:
        # bug in measure?
        # testing single measure first 
        images = []
        while len(images) < n_shots:
            measurement = self.single_measure()
            if len(measurement):
                images += [measurement]
        # fit profile if requested
        if self.fit_profile:
            results = {}
            for i, ele in enumerate(images):
                temp = {}
                rms_x = np.array(np.sum(ele["processed_image"],axis=0))
                rms_y = np.array(np.sum(ele["processed_image"],axis=1))
                temp['rms_x'] = self.fitting_tool.fit_projection(rms_x)
                temp['rms_y'] = self.fitting_tool.fit_projection(rms_y)
                #results += [self.fitting_tool.fit_projection(ele["processed_image"])]
                results['image_' + str(i)] = temp
            # combine images with profile info, hnmmm??? need to dump all pydantic info here?
            print(results)
            final_results = {}
        else:
            # concat list elements into a single dict
            final_results = {}

        # no attribute dump controller 
        # if self.save_data:
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
        print('processing image')
        processed_image = self.image_processor.process(raw_image)
        print('processing image')

        return {"raw_image": raw_image, "processed_image": processed_image}
