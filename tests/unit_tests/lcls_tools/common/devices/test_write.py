import unittest
from unittest.mock import patch, Mock

from lcls_tools.common.devices.yaml.write import YAMLWriter

class TestWrite(unittest.TestCase):

    def test_single_device_types(self):
        writer = YAMLWriter()
        writer.generator = Mock()
        mock_dict = {'magnets': writer.generator.extract_magnets,
                     'screens': writer.generator.extract_screens,
                     'wires': writer.generator.extract_wires,
                     'lblms': writer.generator.extract_lblms,
                     'bpms': writer.generator.extract_bpms,
                     'tcavs': writer.generator.extract_tcavs}
        area = 'None'
        for k, v in mock_dict.items():
            device_types = k
            writer._construct_yaml_contents(area=area, device_types=device_types)
            assert(v.called)

