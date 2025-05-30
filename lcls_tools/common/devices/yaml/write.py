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

        # Generate Magnet content
        magnets = self.generator.extract_magnets(
            area=area,
        )
        if magnets:
            file_contents["magnets"] = magnets

        # Generate Screens content
        screens = self.generator.extract_screens(
            area=area,
        )
        if screens:
            file_contents["screens"] = screens

        # Generate Wire content
        wires = self.generator.extract_wires(
            area=area,
        )
        if wires:
            file_contents["wires"] = wires

        # Generate LBLM content
        lblms = self.generator.extract_lblms(
            area=area,
        )
        if lblms:
            file_contents["lblms"] = lblms

        # Generate BPM content
        bpms = self.generator.extract_bpms(
            area=area,
        )
        if bpms:
            file_contents["bpms"] = bpms

        # Generate BPM content
        tcavs = self.generator.extract_tcavs(
            area=area,
        )
        if tcavs and area == "DIAG0":
            file_contents["tcavs"] = tcavs

        if file_contents:
            return file_contents
        return None

    def write_yaml_file(self, area: Optional[str] = "GUNB", location=None) -> None:
        if area not in self.generator.areas:
            raise RuntimeError(
                f"Area {area} provided is not a known machine area.",
            )
        if location is None:
            location = "lcls_tools/common/devices/yaml/"
        filename = area + ".yaml"
        fullpath = os.path.join(location, filename)
        yaml_output = self._constuct_yaml_contents(area=area)
        if yaml_output:
            with open(fullpath, "w") as file:
                yaml.safe_dump(yaml_output, file)


def write(location=None):
    writer = YAMLWriter()
    areas = writer.areas
    for area in areas:
        writer.write_yaml_file(area, location)


if __name__ == "__main__":
    write()
