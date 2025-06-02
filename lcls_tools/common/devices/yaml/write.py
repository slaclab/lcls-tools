import yaml
import os
from lcls_tools.common.devices.yaml.generate import YAMLGenerator
from typing import Optional, List, Dict
import collections.abc


class YAMLWriter:
    def __init__(self, location=None):
        if location is None:
            location = "lcls_tools/common/devices/yaml/"
        self.out_location = location
        self.generator = YAMLGenerator()

    @property
    def areas(self) -> List[str]:
        return self.generator.areas

    def _is_area(self, area: str) -> bool:
        return area in self.generator.areas

    def _constuct_yaml_contents(self, area: str) -> Dict[str, str]:
        if area not in self.generator.areas:
            raise RuntimeError(
                f"Area {area} provided is not a known machine area.",
            )
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

    def _yaml_dump(self, area, output):
        filename = area + ".yaml"
        fullpath = os.path.join(self.out_location, filename)
        if output:
            with open(fullpath, "w") as file:
                yaml.safe_dump(output, file)

    def _get_current(self, area):
        area_location = self.out_location + area + ".yaml"
        with open(area_location, "r") as file:
            res = yaml.safe_load(file)
        return res

    def overwrite(self, area: Optional[str] = "GUNB") -> None:
        yaml_output = self._constuct_yaml_contents(area=area)
        self._yaml_dump(area, yaml_output)

    def _greedy_update(self, target, update):
        for k, v in update.items():
            if isinstance(v, collections.abc.Mapping):
                target[k] = self._greedy_update(target.get(k, {}), v)
            else:
                target[k] = v
        return target

    def _lazy_update(self, target, update):
        for k, v in update.items():
            if isinstance(v, collections.abc.Mapping):
                target[k] = self._lazy_update(target.get(k, {}), v)
            else:
                if k not in target:
                    target[k] = v
        return target

    def greedy_write(self, area: Optional[str] = "GUNB") -> None:
        current = self._get_current(area)
        update = self._constuct_yaml_contents(area=area)
        yaml_output = self._greedy_update(current, update)
        self._yaml_dump(area, yaml_output)

    def lazy_write(self, area: Optional[str] = "GUNB") -> None:
        current = self._get_current(area)
        update = self._constuct_yaml_contents(area=area)
        yaml_output = self._lazy_update(current, update)
        self._yaml_dump(area, yaml_output)


def write(mode="overwrite", areas=None, location=None):
    writer = YAMLWriter(location=location)
    if areas is None:
        areas = writer.areas
    match mode:
        case "overwrite":
            write = writer.overwrite
        case "greedy":
            write = writer.greedy_write
        case "lazy":
            write = writer.lazy_write
    for area in areas:
        write(area)


if __name__ == "__main__":
    write()
