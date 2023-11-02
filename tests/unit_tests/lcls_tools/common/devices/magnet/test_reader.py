from lcls_tools.common.devices.magnet.reader import create_magnet, _find_yaml_file
from lcls_tools.common.devices.magnet.model import Magnet, MagnetCollection
import unittest
import os


class TestMagnetReader(unittest.TestCase):
    def setUp(self) -> None:
        self.config_location = "./tests/datasets/devices/config/magnet/"
        self.typical_config = os.path.join(self.config_location, "typical_magnet.yaml")
        self.bad_config = os.path.join(self.config_location, "bad_magnet.yaml")
        return super().setUp()

    def test_bad_file_location_raises_when_finding(self):
        with self.assertRaises(FileNotFoundError):
            _find_yaml_file(yaml_filename="bad-filename.yaml")

    def test_bad_file_location_when_creating_magnet_returns_none(self):
        self.assertIsNone(create_magnet(yaml_filename="bad-filename.yml"))

    def test_no_file_location_when_creating_magnet_returns_none(self):
        self.assertIsNone(create_magnet(yaml_filename=None))

    def test_magnet_name_not_in_file_when_creating_magnet_returns_none(self):
        self.assertIsNone(
            create_magnet(yaml_filename=self.typical_config, name="BAD-MAGNET-NAME")
        )

    def test_config_with_no_control_information_returns_none(self):
        self.assertIsNone(create_magnet(self.bad_config, "SOL2B"))

    def test_config_with_no_metadata_returns_none(self):
        self.assertIsNone(create_magnet(self.bad_config, "SOL1B"))

    def test_create_magnet_with_only_config_creates_all_magnets(self):
        result = create_magnet(yaml_filename=self.typical_config)
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
            yaml_filename=self.typical_config,
            name=name,
        )
        self.assertNotIsInstance(result, MagnetCollection)
        self.assertIsInstance(result, Magnet)
