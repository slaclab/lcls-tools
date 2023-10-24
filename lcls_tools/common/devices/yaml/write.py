import yaml
import os
from lcls_tools.common.devices.yaml.generate import YAMLGenerator
from typing import Optional


class YAMLWriter:
    def __init__(self):
        self.generator = YAMLGenerator()
        self.machine_areas = self.generator.areas

    def _is_area(self, area: str):
        return area in self._machine_areas

    def _constuct_yaml_contents(self, area: str) -> dict:
        file_contents = {}
        file_contents["magnets"] = self.generator.extract_magnets(
            area=area,
        )
        file_contents["screens"] = self.generator.extract_screens(
            area=area,
        )
        return file_contents

    def write_yaml_file(self, area: Optional[str] = "GUNB") -> None:
        if area not in self.machine_areas:
            raise RuntimeError(
                f"Area {area} provided is not a known machine area.",
            )
        filename = area + ".yaml"
        location = "lcls_tools/common/devices/yaml/"
        fullpath = os.path.join(location, filename)
        yaml_output = self._constuct_yaml_contents(area=area)
        with open(fullpath, "w") as file:
            yaml.safe_dump(yaml_output, file)
