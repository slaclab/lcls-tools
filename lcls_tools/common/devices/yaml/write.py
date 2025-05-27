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

    def _construct_yaml_contents(self, area: str, device_types: List[str] = None) -> Dict[str, str]:
        if device_types is None:
            device_types = ['magnets', 'screens', 'wires', 'lblms', 'bpms', 'tcavs']

        file_contents = {}

        if 'magnets' in device_types:
            # Generate Magnet content
            magnets = self.generator.extract_magnets(
                area=area,
            )
            if magnets:
                file_contents["magnets"] = magnets

        if 'screens' in device_types:
            # Generate Screens content
            screens = self.generator.extract_screens(
                area=area,
            )
            if screens:
                file_contents["screens"] = screens

        if 'wires' in device_types:
            # Generate Wire content
            wires = self.generator.extract_wires(
                area=area,
            )
            if wires:
                file_contents["wires"] = wires

        if 'lblms' in device_types:
            # Generate LBLM content
            lblms = self.generator.extract_lblms(
                area=area,
            )
            if lblms:
                file_contents["lblms"] = lblms

        if 'bpms' in device_types:
            # Generate BPM content
            bpms = self.generator.extract_bpms(
                area=area,
            )
            if bpms:
                file_contents["bpms"] = bpms

        if 'tcavs' in device_types:
            # Generate BPM content
            tcavs = self.generator.extract_tcavs(
                area=area,
            )
            if tcavs and area == "DIAG0":
                file_contents["tcavs"] = tcavs

        if file_contents:
            return file_contents
        return None

    def write_yaml_file(self, area: Optional[str] = "GUNB", device_types = None) -> None:
        if area not in self.generator.areas:
            raise RuntimeError(
                f"Area {area} provided is not a known machine area.",
            )
        filename = area + ".yaml"
        location = "lcls_tools/common/devices/yaml/"
        fullpath = os.path.join(location, filename)
        yaml_output = self._constuct_yaml_contents(area=area, device_types=device_types)
        if yaml_output:
            with open(fullpath, "w") as file:
                yaml.safe_dump(yaml_output, file)

def write(device_types: List[str] = None):
    writer = YAMLWriter()
    areas = writer.areas
    [writer.write_yaml_file(area) for area in areas]


if __name__ == "__main__":
    write()
    
