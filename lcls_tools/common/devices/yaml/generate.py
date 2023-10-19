import csv
import os
import yaml


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

    def _construct_information_from_element(self, element):
        return {"controls_information": {
                    "control_name": element["Control System Name"],
                },
                "metadata": {
                    "beam_path": element["Beampath"],
                    "area": element["Area"],
                    "sum_l_meters": element["SumL (m)"],
                },
            }

    def extract_magnets(self, area: str = "GUNB") -> dict:
        required_magnet_types = ["SOLE", "QUAD", "XCOR", "YCOR", "BEND"]
        magnet_elements = [
            element
            for element in self.elements
            if element["Keyword"] in required_magnet_types and element["Area"] == area
        ]
        # Must have passed an area that does not exist!
        if len(magnet_elements) < 1:
            raise RuntimeError("Area provided not found in magnet list.")
        # Fill in the dict that will become the yaml file
        yaml_magnets = {}
        for magnet in magnet_elements:
            yaml_magnets.update({magnet["Element"]: {}})
            magnet_yaml_template = self._construct_information_from_element(magnet)
            yaml_magnets[magnet["Element"]].update(magnet_yaml_template)

        return yaml_magnets

    def extract_screens(self, area : str = "HTR"):
        required_screen_types = ["PROF"]
        screen_elements = [
            element
            for element in self.elements
            if element["Keyword"] in required_screen_types and element["Area"] == area
        ]
        # Must have passed an area that does not exist!
        if len(screen_elements) < 1:
            raise RuntimeError("Area provided not found in screen list.")
        # Fill in the dict that will become the yaml file
        yaml_screens = {}
        for screen in screen_elements:
            yaml_screens.update({screen["Element"]: {}})
            screen_yaml_template = self._construct_information_from_element(screen)
            yaml_screens[screen["Element"]].update(screen_yaml_template)

        return yaml_screens
