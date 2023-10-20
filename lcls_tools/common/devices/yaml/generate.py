import csv
import os
import yaml
from typing import Union, List, Dict, Optional


class YAMLGenerator:
    def __init__(
        self,
        csv_location="./lcls_tools/common/devices/yaml/lcls_elements.csv",
    ):
        if not os.path.isfile(csv_location):
            raise FileNotFoundError(f"Could not find {csv_location}")
        self.csv_reader = None
        self._required_fields = [
            "Element",
            "Control System Name",
            "Area",
            "Keyword",
            "Beampath",
            "SumL (m)",
        ]

        self.elements = None
        with open(csv_location, "r") as file:
            self.csv_reader = csv.DictReader(f=file)

            # make the elements from csv stripped out with only information we need
            def _is_required_field(pair: tuple):
                key, _ = pair
                return key in self._required_fields

            self.elements = [
                dict(filter(_is_required_field, element.items()))
                for element in self.csv_reader
            ]
        if not self.elements:
            raise RuntimeError(
                "Did not generate elements, please look at lcls_elements.csv."
            )

    def _construct_information_from_element(
        self, element, pv_information: Optional[Dict[str, str]] = {}
    ):
        return {
            "controls_information": {
                "control_name": element["Control System Name"],
                "PVs": pv_information,
            },
            "metadata": {
                "beam_path": element["Beampath"],
                "area": element["Area"],
                "sum_l_meters": element["SumL (m)"],
            },
        }

    def extract_magnets(self, area: Union[str, List[str]] = "GUNB") -> dict:
        required_magnet_types = ["SOLE", "QUAD", "XCOR", "YCOR", "BEND"]
        if not isinstance(area, list):
            area = list(area)
        yaml_magnets = {}
        for _area in area:
            magnet_elements = [
                element
                for element in self.elements
                if element["Keyword"] in required_magnet_types
                and element["Area"] == _area
            ]
            # Must have passed an area that does not exist!
            if len(magnet_elements) < 1:
                raise RuntimeError("Area provided not found in magnet list.")
            # Fill in the dict that will become the yaml file
            for magnet in magnet_elements:
                pv_info = {
                    "bact": magnet["Control System Name"] + ":BACT",
                    "bctrl": magnet["Control System Name"] + ":BCTRL",
                    "bcon": magnet["Control System Name"] + ":BCON",
                    "bdes": magnet["Control System Name"] + ":BDES",
                    "ctrl": magnet["Control System Name"] + ":CTRL",
                }
                yaml_magnets.update({magnet["Element"]: {}})
                magnet_yaml_template = self._construct_information_from_element(
                    magnet, pv_information=pv_info
                )
                yaml_magnets[magnet["Element"]].update(magnet_yaml_template)
        return yaml_magnets

    def extract_screens(self, area: Union[str, List[str]] = ["HTR"]):
        if not isinstance(area, list):
            area = list(area)
        yaml_screens = {}
        for _area in area:
            required_screen_types = ["PROF"]
            screen_elements = [
                element
                for element in self.elements
                if element["Keyword"] in required_screen_types
                and element["Area"] == _area
            ]
            # Must have passed an area that does not exist!
            if len(screen_elements) < 1:
                raise RuntimeError("Area provided not found in screen list.")
            # Fill in the dict that will become the yaml file
            for screen in screen_elements:
                yaml_screens.update({screen["Element"]: {}})
                screen_yaml_template = self._construct_information_from_element(screen)
                yaml_screens[screen["Element"]].update(screen_yaml_template)
        return yaml_screens
