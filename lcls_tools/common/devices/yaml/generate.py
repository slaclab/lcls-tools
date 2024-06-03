import csv
import os
from typing import Any, Union, List, Dict, Optional
import meme.names
import numpy as np
from lcls_tools.common.devices.yaml.metadata import (
    get_magnet_metadata,
    get_screen_metadata,
)
from lcls_tools.common.devices.yaml.controls_information import (
    get_magnet_controls_information,
    get_screen_controls_information,
)


class YAMLGenerator:
    def __init__(
        self,
        csv_location="./lcls_tools/common/devices/yaml/lcls_elements.csv",
    ):
        self.csv_location = csv_location
        if not os.path.isfile(csv_location):
            raise FileNotFoundError(f"Could not find {csv_location}")
        self._required_fields = [
            "Element",
            "Control System Name",
            "Area",
            "Keyword",
            "Beampath",
            "SumL (m)",
        ]
        self.elements = self._filter_elements_by_fields(self._required_fields)
        self._areas = self.extract_areas()
        self._beam_paths = self.extract_beampaths()

    def _filter_elements_by_fields(self, required_fields: List[str]) -> Dict[str, Any]:
        csv_reader = None
        with open(self.csv_location, "r") as file:
            # convert csv file into dictionary for filtering
            csv_reader = csv.DictReader(f=file)

            # make the elements from csv stripped out with only information we need
            def _is_required_field(pair: tuple):
                key, _ = pair
                return key in required_fields

            # only store the required fields from lcls_elements, there are lots more!
            elements = [
                dict(filter(_is_required_field, element.items()))
                for element in csv_reader
            ]
        if not elements:
            raise RuntimeError(
                "Did not generate elements, please look at lcls_elements.csv."
            )
        return elements

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
        self,
        element,
        pv_information: Optional[Dict[str, str]] = {},
        additional_metadata_fields: Dict[str, Any] = {},
        additional_control_fields: Dict[str, Any] = {},
    ):
        """
        Generates a dictionary with only the relevant information we want
        from the Dict that lcls_elements.csv is loaded into.
        """
        sum_l_meters = float(element["SumL (m)"]) if element["SumL (m)"] else None
        device_information = {
            "controls_information": {
                "control_name": element["Control System Name"],
                "PVs": pv_information,
            },
            "metadata": {
                "beam_path": [
                    item.strip() for item in element["Beampath"].split(",") if item
                ],
                "area": element["Area"],
                "type": element["Keyword"],
                "sum_l_meters": (
                    float(np.format_float_positional(sum_l_meters, precision=3))
                    if sum_l_meters is not None
                    else None
                ),
            },
        }
        [
            device_information["metadata"].update({field_name: field_value})
            for field_name, field_value in additional_metadata_fields.items()
        ]
        [
            device_information["controls_information"].update(
                {field_name: element[field_name]}
            )
            for field_name in additional_control_fields.items()
        ]
        return device_information

    def _construct_pv_list_from_control_system_name(
        self, name, search_with_handles: Optional[Dict[str, str]]
    ) -> Dict[str, str]:
        if name == "":
            raise RuntimeError("No control system name provided for meme search.")
        # Use the control system name to get all PVs associated with device
        pv_dict = {}
        for search_term, handle in search_with_handles.items():
            # End of the PV name is implied in search_term
            try:
                pv_list = meme.names.list_pvs(name + ":" + search_term, sort_by="z")
                # We expect to have ZERO or ONE result returned from meme
                if pv_list != list():
                    if len(pv_list) == 1:
                        # get the pv out of the results
                        pv = pv_list[0]
                        if not handle:
                            # if the user has not provided their own handle then
                            # split by colon, grab the last part of the string as a handle
                            name_in_yaml = pv.split(":")[-1].lower()
                        else:
                            # user has provided their own handle.
                            name_in_yaml = handle
                        # add it to the dictionary of PVs
                        pv_dict[name_in_yaml] = pv
                    else:
                        raise RuntimeError(
                            f"Did not return unique PV search result from MEME, please check MEME {name}:{search_term}"
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
        pv_search_terms=Optional[List[str]],
    ):
        if not isinstance(area, list):
            machine_areas = [area]
        else:
            machine_areas = area
        yaml_devices = {}
        elements = self._filter_elements_by_fields(
            required_fields=self._required_fields
        )
        for _area in machine_areas:
            device_elements = [
                element
                for element in elements
                if element["Keyword"] in required_types and element["Area"] == _area
            ]
        # Must have passed an area that does not exist or we don't have that device in this area!
        if len(device_elements) < 1:
            print(f"No devices of types {required_types} found in area {area}")
            return
        # Fill in the dict that will become the yaml file
        for device in device_elements:
            # We need a control-system-name
            if device["Control System Name"] != "":
                try:
                    # grab the pv information for this element using the search_list
                    pv_info = self._construct_pv_list_from_control_system_name(
                        name=device["Control System Name"],
                        search_with_handles=pv_search_terms,
                    )
                except RuntimeError as rte:
                    print(rte)
                # add device and information to the yaml-contents
                yaml_devices.update(
                    {
                        device["Element"]: self._construct_information_from_element(
                            device,
                            pv_information=pv_info,
                        )
                    }
                )
        return yaml_devices

    def add_to_device_metadata(
        self,
        device_data: Dict[str, Any],
        additional_metadata: Dict[str, Any] = {},
    ) -> Dict[str, Any]:
        for device in device_data.keys():
            try:
                device_data[device]["metadata"].update(additional_metadata[device])
            except KeyError:
                print("No additional metadata found for ", device)

        return device_data

    def add_to_device_controls_information(
        self,
        device_data: Dict[str, Any],
        additional_controls_information: Dict[str, Any] = {},
    ) -> Dict[str, Any]:
        for device in device_data.keys():
            try:
                device_data[device]["controls_information"].update(
                    additional_controls_information[device]
                )
            except KeyError:
                print("No additional controls information found for ", device)
        return device_data

    def add_extra_data_to_device(
        self,
        device_data: Dict[str, Any],
        additional_controls_information: Dict[str, Any] = {},
        additional_metadata: Dict[str, Any] = {},
    ) -> Dict[str, Any]:
        complete_device_data = {}
        complete_device_data.update(
            self.add_to_device_metadata(
                device_data=device_data,
                additional_metadata=additional_metadata,
            ),
        )
        complete_device_data.update(
            self.add_to_device_controls_information(
                device_data=complete_device_data,
                additional_controls_information=additional_controls_information,
            ),
        )
        return complete_device_data

    def extract_magnets(self, area: Union[str, List[str]] = "GUNB") -> dict:
        required_magnet_types = ["SOLE", "QUAD", "XCOR", "YCOR", "BEND"]
        # PV suffix as the key, the name we want to store it as in yaml file as the value
        # None implies that we are happen using the PV suffix (lowercase) as the name in yaml
        possible_magnet_pvs = {
            "BACT": None,
            "BCTRL": None,
            "BCON": None,
            "BDES": None,
            "CTRL": None,
            "BMIN": None,
            "BMAX": None,
        }
        # should be structured {MAD-NAME : {field_name : value, field_name_2 : value}, ... }
        additional_metadata_data = get_magnet_metadata()
        # should be structured {MAD-NAME : {field_name : value, field_name_2 : value}, ... }
        additional_controls_data = get_magnet_controls_information()
        basic_magnet_data = self.extract_devices(
            area=area,
            required_types=required_magnet_types,
            pv_search_terms=possible_magnet_pvs,
        )
        if basic_magnet_data:
            complete_magnet_data = self.add_extra_data_to_device(
                device_data=basic_magnet_data,
                additional_controls_information=additional_controls_data,
                additional_metadata=additional_metadata_data,
            )
            return complete_magnet_data
        else:
            return {}

    def extract_screens(self, area: Union[str, List[str]] = ["HTR"]):
        required_screen_types = ["PROF"]
        # PV suffix as the key, the name we want to store it as in yaml file as the value
        # None implies that we are happen using the PV suffix (lowercase) as the name in yaml
        possible_screen_pvs = {
            "IMAGE": "image",
            "Image:ArrayData": "image",
            "RESOLUTION": None,
            "Image:ArraySize0_RBV": "n_row",
            "Image:ArraySize1_RBV": "n_col",
            "N_OF_COL": "n_col",
            "N_OF_ROW": "n_row",
            "N_OF_BITS": "n_bits",
        }
        # should be structured {MAD-NAME : {field_name : value, field_name_2 : value}, ... }
        additional_metadata_data = get_screen_metadata()
        # should be structured {MAD-NAME : {field_name : value, field_name_2 : value}, ... }
        additional_controls_data = get_screen_controls_information()
        basic_screen_data = self.extract_devices(
            area=area,
            required_types=required_screen_types,
            pv_search_terms=possible_screen_pvs,
        )
        if basic_screen_data:
            complete_screen_data = self.add_extra_data_to_device(
                device_data=basic_screen_data,
                additional_controls_information=additional_controls_data,
                additional_metadata=additional_metadata_data,
            )
            return complete_screen_data
        else:
            return {}
