import unittest
import yaml
from lcls_tools.common.devices.area import Area


class TestArea(unittest.TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_area_with_no_magnets(self):
        mock_screen_data = {"screens": {}}
        with open(
            "tests/datasets/devices/config/screen/typical_screen.yaml", "r"
        ) as file:
            mock_screen_data["screens"] = yaml.safe_load(file)
        area = Area(**mock_screen_data)
        self.assertIsNone(area.magnet_collection)
        self.assertIsNone(area.magnets)
