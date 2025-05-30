import os
import shutil
import unittest
import lcls_tools.common.devices.yaml.write
from unittest.mock import patch, PropertyMock
import yaml


class TestWrite(unittest.TestCase):
    def setUp(self):
        self.data_location = (
            "tests/unit_tests/lcls_tools/common/devices/yaml/test_data/"
        )
        area_location = self.data_location + "AREA.yaml"
        with open(area_location, "r") as file:
            self.area = yaml.safe_load(file)
        self.generate_patcher = patch(
            "lcls_tools.common.devices.yaml.write.YAMLGenerator"
        )
        self.mock_generate = self.generate_patcher.start()
        instance = self.mock_generate.return_value
        instance.extract_magnets.return_value = {}
        instance.extract_screens.return_value = self.area["screens"]
        instance.extract_wires.return_value = self.area["wires"]
        instance.extract_lblms.return_value = {}
        instance.extract_bpms.return_value = {}
        instance.extract_tcavs.return_value = {}
        type(instance).areas = PropertyMock(return_value=["AREA"])
        testbed = "tests/unit_tests/lcls_tools/common/devices/yaml/testbed/"
        if not os.path.exists(testbed):
            os.makedirs(testbed)
        self.testbed = testbed

    def tearDown(self):
        shutil.rmtree(self.testbed)
        self.generate_patcher.stop()

    def test_overwrite_yaml(self):
        result_location = self.testbed
        partial_area = self.data_location + "PARTIALAREA.yaml"
        shutil.copyfile(partial_area, result_location + "AREA.yaml")
        lcls_tools.common.devices.yaml.write.write(location=result_location)
        result_location += "AREA.yaml"
        with open(result_location, "r") as file:
            res = yaml.safe_load(file)
        self.assertEqual(self.area, res)
        os.remove(result_location)

    def test_greedy_write_yaml(self):
        result_location = self.testbed
        partial_area = self.data_location + "PARTIALAREA.yaml"
        shutil.copyfile(partial_area, result_location + "AREA.yaml")
        lcls_tools.common.devices.yaml.write.write(
            location=result_location, mode="greedy"
        )
        result_location += "AREA.yaml"
        with open(result_location, "r") as file:
            res = yaml.safe_load(file)
        self.assertIn("wires", res)
        self.assertIn("magnets", res)
        self.assertIn("old_stuff", res["screens"]["FAKESCREEN"])
