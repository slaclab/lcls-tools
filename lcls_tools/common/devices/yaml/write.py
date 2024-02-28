import yaml
import os
from lcls_tools.common.devices.yaml.generate import YAMLGenerator
from typing import Optional, List, Dict


class YAMLWriter:
    def __init__(self):
        self.generator = YAMLGenerator()

    @property
    def areas(self) -> List[str]:
        return self.generator.areas

    def _is_area(self, area: str) -> bool:
        return area in self.generator.areas

    def _constuct_yaml_contents(self, area: str) -> Dict[str, str]:
        file_contents = {}
        magnets = self.generator.extract_magnets(
            area=area,
        )
        if magnets:
            file_contents["magnets"] = magnets
        screens = self.generator.extract_screens(
            area=area,
        )
        if screens:
            file_contents["screens"] = screens

        if file_contents:
            return file_contents
        return None

    def write_yaml_file(self, area: Optional[str] = "GUNB") -> None:
        if area not in self.generator.areas:
            raise RuntimeError(
                f"Area {area} provided is not a known machine area.",
            )
        filename = area + ".yaml"
        location = "lcls_tools/common/devices/yaml/"
        fullpath = os.path.join(location, filename)
        yaml_output = self._constuct_yaml_contents(area=area)
        if yaml_output:
            with open(fullpath, "w") as file:
                yaml.safe_dump(yaml_output, file)


if __name__ == "__main__":
    writer = YAMLWriter()
    areas = writer.areas
    [writer.write_yaml_file(area) for area in areas]
