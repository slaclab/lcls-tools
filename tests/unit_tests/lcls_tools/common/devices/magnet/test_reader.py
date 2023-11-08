from lcls_tools.common.devices.magnet.reader import create_magnet, _find_yaml_file
from lcls_tools.common.devices.magnet.magnet import Magnet, MagnetCollection
import unittest
from unittest.mock import patch, MagicMock
import os


class TestMagnetReader(unittest.TestCase):
    def setUp(self) -> None:
        self.config_location = "./tests/datasets/devices/config/magnet/"
        self.typical_config = os.path.join(self.config_location, "typical_magnet.yaml")
        self.bad_config = os.path.join(self.config_location, "bad_magnet.yaml")
        return super().setUp()

    def test_bad_file_location_raises_when_finding(self):
        with self.assertRaises(FileNotFoundError):
            _find_yaml_file(area="bad-area")

    def test_bad_file_location_when_creating_magnet_returns_none(self):
        self.assertIsNone(create_magnet("bad-area"))

    def test_no_file_location_when_creating_magnet_returns_none(self):
        self.assertIsNone(create_magnet())

    def test_magnet_name_not_in_file_when_creating_magnet_returns_none(self):
        self.assertIsNone(create_magnet(area="GUNB", name="BAD-MAGNET-NAME"))

    @patch(
        "lcls_tools.common.devices.magnet.reader._find_yaml_file",
        new_callable=MagicMock(),
    )
    def test_config_with_no_control_information_returns_none(self, mock_find_yaml):
        mock_find_yaml.return_value = self.bad_config
        self.assertIsNone(create_magnet(area="GUNX", name="CQ02B"))

    @patch(
        "lcls_tools.common.devices.magnet.reader._find_yaml_file",
        new_callable=MagicMock(),
    )
    def test_config_with_no_metadata_returns_none(self, mock_find_yaml):
        mock_find_yaml.return_value = self.bad_config
        self.assertIsNone(create_magnet(area="GUNX", name="SOL1B"))

    def test_create_magnet_with_only_config_creates_all_magnets(self):
        result = create_magnet(area="GUNB")
        self.assertIsInstance(result, MagnetCollection)
        for name in [
            "SOL2B",
            "SOL1B",
        ]:
            self.assertIn(name, result.magnets, msg=f"expected {name} in {result}.")
            self.assertIsInstance(result.magnets[name], Magnet)

    def test_create_magnet_with_config_and_name_creates_one_magnet(self):
        name = "SOL1B"
        result = create_magnet(
            area="GUNB",
            name=name,
        )
        self.assertNotIsInstance(result, MagnetCollection)
        self.assertIsInstance(result, Magnet)
