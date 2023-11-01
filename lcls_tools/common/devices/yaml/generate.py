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
            # convert csv file into dictionary for filtering
            self.csv_reader = csv.DictReader(f=file)

            # make the elements from csv stripped out with only information we need
            def _is_required_field(pair: tuple):
                key, _ = pair
                return key in self._required_fields
            # only store the required fields from lcls_elements, there are lots more!
            self.elements = [
                dict(filter(_is_required_field, element.items()))
                for element in self.csv_reader
            ]
        if not self.elements:
            raise RuntimeError(
                "Did not generate elements, please look at lcls_elements.csv."
            )
        self._areas = self.extract_areas()
        self._beam_paths = self.extract_beampaths()

    def extract_areas(self) -> list:
        areas = []
        [
            areas.append(element["Area"])
            for element in self.elements
            if element["Area"] not in areas
        ]
        return areas

    @property
    def areas(self) -> list:
        return self._areas

    def extract_beampaths(self) -> list:
        beampaths = []
        [
            beampaths.append(beampath)
            for element in self.elements
            for beampath in element["Beampath"].split(",")
            if beampath not in beampaths and beampath != ""
        ]
        return beampaths

    @property
    def beam_paths(self) -> list:
        return self._beam_paths

    def _construct_information_from_element(
        self, element, pv_information: Optional[Dict[str, str]] = {}
    ):
        """
        Generates a dictionary with only the relevant information we want
        from the Dict that lcls_elements.csv is loaded into.
        """
        sum_l_meters = float(element["SumL (m)"]) if element["SumL (m)"] else None
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
                "sum_l_meters": float(
                    np.format_float_positional(sum_l_meters, precision=3)
                    if sum_l_meters
                    else None
                ),
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
                # We expect to have ZERO or ONE result returned from meme
                if pv_list != list():
                    if len(pv_list) == 1:
                        # get the pv out of the results
                        pv = pv_list[0]
                        # split by colon, grab the last part of the string as a handle
                        handle = pv.split(":")[-1].lower()
                        # add it to the dictionary of PVs
                        pv_dict[handle] = pv
                    else:
                        raise RuntimeError(
                            f"Did not return unique PV search result from MEME, please check MEME {name}:{search_list}"
                        )
            except TimeoutError as toe:
                print(
                    f'Unable connect to MEME.name service when searching for {name + ":" + search_term}.'
                )
                print(toe)
        return pv_dict

    def extract_devices(
        self,
        area: Union[str, List[str]],
        required_types=Optional[List[str]],
        pv_search_list=Optional[List[str]],
    ):
        if not isinstance(area, list):
            machine_areas = [area]
        else:
            machine_areas = area
        yaml_devices = {}
        for _area in machine_areas:
            device_elements = [
                element
                for element in self.elements
                if element["Keyword"] in required_types and element["Area"] == _area
            ]
        # Must have passed an area that does not exist or we don't have that device in this area!
        if len(device_elements) < 1:
            print(f"No devices found in area {area}")
            return
        # Fill in the dict that will become the yaml file
        for device in device_elements:
            # We need a control-system-name
            if device["Control System Name"] != "":
                try:
                    # grab the pv information for this element using the search_list
                    pv_info = self._construct_pv_list_from_control_system_name(
                        device["Control System Name"],
                        pv_search_list,
                    )
                except RuntimeError as rte:
                    print(rte)
                # add device and information to the yaml-contents
                yaml_devices.update(
                    {
                        device["Element"]: self._construct_information_from_element(
                            device, pv_information=pv_info
                        )
                    }
                )
        return yaml_devices

    def extract_magnets(self, area: Union[str, List[str]] = "GUNB") -> dict:
        required_magnet_types = ["SOLE", "QUAD", "XCOR", "YCOR", "BEND"]
        magnet_pv_search_list = ["BACT", "BCTRL", "BCON", "BDES", "CTRL"]
        return self.extract_devices(
            area=area,
            required_types=required_magnet_types,
            pv_search_list=magnet_pv_search_list,
        )

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
        return self.extract_devices(
            area=area,
            required_types=required_screen_types,
            pv_search_list=possible_screen_pvs,
        )
