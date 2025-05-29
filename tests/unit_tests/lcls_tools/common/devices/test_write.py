import unittest
from unittest.mock import patch

import lcls_tools.common.devices.yaml.write


@patch("lcls_tools.common.devices.yaml.write.YAMLGenerator")
class TestWrite(unittest.TestCase):
    def test_single_device_types(self, generator_class):
        writer = lcls_tools.common.devices.yaml.write.YAMLWriter()
        generator = writer.generator
        mock_dict = {
            "magnets": generator.extract_magnets,
            "screens": generator.extract_screens,
            "wires": generator.extract_wires,
            "lblms": generator.extract_lblms,
            "bpms": generator.extract_bpms,
            "tcavs": generator.extract_tcavs,
        }
        area = "None"
        for k, v in mock_dict.items():
            device_types = k
            writer._construct_yaml_contents(area=area, device_types=device_types)
            assert v.called
