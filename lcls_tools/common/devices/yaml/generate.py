import csv
import os
from typing import Union, List, Dict, Optional
import meme.names
import numpy as np


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
        self.areas = self.extract_areas()
        self.beam_paths = self.extract_beampaths()

    def extract_areas(self) -> list:
        areas = []
        [
            areas.append(element["Area"])
            for element in self.elements
            if element["Area"] not in areas
        ]
        return areas

    def get_areas(self) -> list:
        return self.areas

    def extract_beampaths(self) -> list:
        beampaths = []
        [
            beampaths.append(beampath)
            for element in self.elements
            for beampath in element["Beampath"].split(",")
            if beampath not in beampaths and beampath != ""
        ]
        return beampaths

    def get_beam_paths(self) -> list:
        return self.beam_paths

    def _construct_information_from_element(
        self, element, pv_information: Optional[Dict[str, str]] = {}
    ):
        sum_l_meters = float(element["SumL (m)"]) if element["SumL (m)"] else -1.0,
        return {
            "controls_information": {
                "control_name": element["Control System Name"],
                "PVs": pv_information,
            },
            "metadata": {
                "beam_path": [
                    item.strip() for item in element["Beampath"].split(",") if item
                ],
                "area": element["Area"],
                "sum_l_meters": np.format_float_positional(sum_l_meters, precision=3)
            },
        }

    def _construct_pv_list_from_control_system_name(
        self, name, search_list: Optional[List[str]]
    ) -> Dict[str, str]:
        if name == "":
            raise RuntimeError("No control system name provided for meme search.")
        # Use the control system name to get all PVs associated with device
        pv_dict = {}
        for search_term in search_list:
            # End of the PV name is implied in search_term
            try:
                pv_list = meme.names.list_pvs(name + ":" + search_term, sort_by="z")
                if pv_list != list():
                    pv = pv_list[0]
                    handle = pv.split(":")[-1].lower()
                    pv_dict[handle] = pv
            except TimeoutError as toe:
                print(
                    f'Unable connect to MEME.name service when searching for {name + ":" + search_term}.'
                )
                print(toe)
        return pv_dict

    def extract_magnets(self, area: Union[str, List[str]] = "GUNB") -> dict:
        required_magnet_types = ["SOLE", "QUAD", "XCOR", "YCOR", "BEND"]
        if not isinstance(area, list):
            machine_areas = [area]
        else:
            machine_areas = area
        yaml_magnets = {}
        for _area in machine_areas:
            magnet_elements = [
                element
                for element in self.elements
                if element["Keyword"] in required_magnet_types
                and element["Area"] == _area
            ]
        # Must have passed an area that does not exist!
        if len(magnet_elements) < 1:
            print(f"No magnets found in area {area}")
            return
        # Fill in the dict that will become the yaml file
        for magnet in magnet_elements:
            if magnet["Control System Name"] != "":
                try:
                    pv_info = self._construct_pv_list_from_control_system_name(
                        magnet["Control System Name"],
                        ["BACT", "BCTRL", "BCON", "BDES", "CTRL"],
                    )
                except RuntimeError as rte:
                    print(rte)
                yaml_magnets.update({magnet["Element"]: {}})
                magnet_yaml_template = self._construct_information_from_element(
                    magnet, pv_information=pv_info
                )
                yaml_magnets[magnet["Element"]].update(magnet_yaml_template)
        return yaml_magnets

    def camera_type():
        # Determine type of camera and PVs
        # Is there a way to get the camera type w/o a list?
        pass

    def extract_screens(self, area: Union[str, List[str]] = ["HTR"]):
        required_screen_types = ["PROF"]
        possible_screen_pvs = [
            "IMAGE",
            "Image:ArrayData",
            "RESOLUTION",
            "Image:ArraySizeX_RBV",
            "Image:ArraySizeY_RBV",
            "N_OF_COL",
            "N_OF_ROW",
            "N_OF_BITS",
        ]
        if not isinstance(area, list):
            machine_areas = [area]
        else:
            machine_areas = area
        for _area in machine_areas:
            screen_elements = [
                element
                for element in self.elements
                if element["Keyword"] in required_screen_types
                and element["Area"] == _area
            ]
        # Must have passed an area that does not exist!
        if len(screen_elements) < 1:
            print(f"No screens found in area {area}")
            return
        # Fill in the dict that will become the yaml file
        yaml_screens = {}
        for screen in screen_elements:
            if screen["Control System Name"] != "":
                yaml_screens.update({screen["Element"]: {}})
                try:
                    pv_info = self._construct_pv_list_from_control_system_name(
                        screen["Control System Name"], possible_screen_pvs
                    )
                except RuntimeError as rte:
                    print(rte)
                screen_yaml_template = self._construct_information_from_element(
                    screen, pv_information=pv_info
                )
                yaml_screens[screen["Element"]].update(screen_yaml_template)
        return yaml_screens
