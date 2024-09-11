from lcls_tools.common.devices.screen import Screen
from lcls_tools.common.data_analysis.fit.gaussian_fit import GaussianFit
from lcls_tools.common.measurements.measurement import Measurement
from pydantic import ConfigDict
import copy


class ScreenBeamProfileMeasurement(Measurement):
    """
    Class that allows for beam profile measurements and fitting
    ------------------------
    Arguments:
    name: str (name of measurement default is beam_profile),
    device: Screen (device that will be performing the measurement),
    beam_fit: method for performing beam profile fit, default is gfit
    fit_profile: bool = True
    ------------------------
    Methods:
    single_measure: measures device and returns raw and processed image
    measure: does multiple measurements and has an option to fit the image
             profiles

    #TODO: DumpController?
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)
    name: str = "beam_profile"
    device: Screen
    beam_fit: GaussianFit = GaussianFit()  # actually want an additional
    # layer before GaussianFit so that beam_fit_tool is a generic fit tool
    # not constrained to be of gaussian fit type
    fit_profile: bool = True

    def single_measure(self) -> dict:
        """
        Function that grabs a single image from the device class
        (typically live beam images) and passes it to the
        image processing class embedded with beam_fit for
        processing (subtraction and cropping)
        returns a dictionary with both the raw and processed dictionary
        """
        raw_image = self.device.image
        processed_image = self.beam_fit.processor.auto_process(raw_image)
        return {"raw_image": raw_image, "processed_image": processed_image}

    def measure(self, n_shots: int = 1) -> dict:
        """
        Measurement function that takes in n_shots as argument
        where n_shots is the number of image profiles
        we would like to measure. Invokes single_measure per shot,
        storing them in a dictionary sorted by shot number
        Then if self.fit_profile = True, fits the profile of the beam
        and concatenates results with the image dictionary sorted by
        shot number
        """
        images = {}
        while len(images) < n_shots:
            measurement = self.single_measure()
            images[len(images)] = measurement

        if self.fit_profile:
            for measurement in images.values():
                self.beam_fit.image = measurement["processed_image"]
                measurement.update(self.beam_fit.beamsize)
        results = copy.deepcopy(images)

        return results
