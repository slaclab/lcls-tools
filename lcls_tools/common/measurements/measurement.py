from abc import ABC, abstractmethod
from typing import Optional
from pydantic import BaseModel, DirectoryPath
from lcls_tools.common.devices.device import Device
from lcls_tools.common.image_processing.image_processing import ImageProcessor
from lcls_tools.common.data_analysis.projection_fit.projection_fit import ProjectionFit

class Measurement(BaseModel, ABC):
    name: str
    save_data: bool = True
    save_location: Optional[DirectoryPath] = None

    @abstractmethod
    def measure(self, **kwargs) -> dict:
        """ Implements a measurement and returns a dictionary with the results"""
        raise NotImplementedError

class ScreenBeamProfile(Measurement):
    name = "beam_profile"
    device: Device
    image_processer: ImageProcessor
    fitting_tool: ProjectionFit
    fit_profile: bool = True

    n_shots: int = 5
    # charge_window: Optional[ChargeWindow] = None

    def measure(self) -> dict:
        images = []
        while len(images) < self.n_shots:
            measurement = self.single_measure()
            if len(measurement):
                images += [self.single_measure()]

        # fit profile if requested
        if self.fit_profile:
            results = []
            for ele in images:
                results += [self.fitting_tool.fit_projection(ele["processed_image"])]

            # combine images with profile info
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

        # should add image to class Device itself as a property other wise not all children inherently have an image property
        raw_image = self.device.image

        # get ICT measurements and return None if not in window
        # if self.charge_window is not None:
           # if not self.charge_window.in_window():
               # return {}

        processed_image = self.image_processer.process(raw_image)
        return {"raw_image": raw_image, "processed_image": processed_image}
