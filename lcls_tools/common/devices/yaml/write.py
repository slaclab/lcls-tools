import yaml
import os
from lcls_tools.common.devices.yaml.generate import YAMLGenerator
from typing import Optional, List, Dict
import collections.abc
import argparse


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

    def _construct_yaml_contents(
        self, area: str, devices: List[str] = None
    ) -> Dict[str, str]:
        if area not in self.generator.areas:
            raise RuntimeError(
                f"Area {area} provided is not a known machine area.",
            )
        file_contents = {}

        extractors = {
            "magnets": self.generator.extract_magnets,
            "screens": self.generator.extract_screens,
            "wires": self.generator.extract_wires,
            "lblms": self.generator.extract_lblms,
            "bpms": self.generator.extract_bpms,
            "tcavs": self.generator.extract_tcavs,
        }

        if devices is None:
            devices = list(extractors.keys())

        for k, v in extractors.items():
            if k in devices:
                device_data = v(area=area)
                if device_data:
                    file_contents[k] = device_data

        if file_contents:
            return file_contents
        return {}

    def _yaml_dump(self, area, output):
        filename = area + ".yaml"
        fullpath = os.path.join(self.out_location, filename)
        if output:
            with open(fullpath, "w") as file:
                yaml.safe_dump(output, file)

    def overwrite(self, area: Optional[str] = "GUNB") -> None:
        yaml_output = self._construct_yaml_contents(area=area)
        self._yaml_dump(area, yaml_output)

    def _get_current(self, area):
        area_location = self.out_location + area + ".yaml"
        if not os.path.exists(area_location):
            return {}
        with open(area_location, "r") as file:
            res = yaml.safe_load(file)
        return res

    def _greedy_update(self, target, update):
        for k, v in update.items():
            if isinstance(v, collections.abc.Mapping):
                target[k] = self._greedy_update(target.get(k, {}), v)
            else:
                target[k] = v
        return target

    def greedy_write(
        self, area: Optional[str] = "GUNB", devices: List[str] = None
    ) -> None:
        current = self._get_current(area)
        update = self._construct_yaml_contents(area=area, devices=devices)
        yaml_output = self._greedy_update(current, update)
        self._yaml_dump(area, yaml_output)

    def _lazy_update(self, target, update):
        for k, v in update.items():
            if isinstance(v, collections.abc.Mapping):
                target[k] = self._lazy_update(target.get(k, {}), v)
            else:
                if k not in target:
                    target[k] = v
        return target

    def lazy_write(
        self, area: Optional[str] = "GUNB", devices: List[str] = None
    ) -> None:
        current = self._get_current(area)
        update = self._construct_yaml_contents(area=area, devices=devices)
        yaml_output = self._lazy_update(current, update)
        self._yaml_dump(area, yaml_output)


def write(mode="overwrite", devices=None, areas=None, location=None):
    yaml_writer = YAMLWriter(location=location)
    if areas is None:
        areas = yaml_writer.areas
    match mode:
        case "overwrite":
            selected_writer = yaml_writer.overwrite
        case "greedy":
            selected_writer = yaml_writer.greedy_write
        case "lazy":
            selected_writer = yaml_writer.lazy_write
    for area in areas:
        selected_writer(area, devices)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="YAML Writer")
    parser.add_argument(
        "-m",
        "--mode",
        choices=["overwrite", "greedy", "lazy"],
        default="overwrite",
        help=(
            "The YAML writing mode. 'overwrite' replaces the YAML with "
            "current data. 'greedy' adds new data and corrects old data. "
            "'lazy' adds new data and leaves old data alone. "
            "Default: %(default)s"
        ),
    )
    parser.add_argument(
        "--devices",
        nargs="+",
        help=(
            "The devices to read from lcls_elements.csv. Use this arg "
            "with --mode greedy or lazy to avoid deleting devices that "
            "aren't currently selected."
        ),
    )
    args = parser.parse_args()
    write(mode=args.mode, devices=args.devices)
