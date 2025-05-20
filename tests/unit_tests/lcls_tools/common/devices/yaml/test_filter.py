import unittest
import lcls_tools.common.devices.yaml.generate as g


class TestFilter(unittest.TestCase):
    def setUp(self) -> None:
        return super().setUp()

    def tearDown(self) -> None:
        return super().tearDown()

    def test_filter_bad_prefix(self):
        csv_location = "tests/datasets/devices/yaml/DIAG0_only_good_element.csv"
        filter_location = "tests/datasets/devices/yaml/filter_stars.yaml"
        generator = g.YAMLGenerator(
            csv_location=csv_location, filter_location=filter_location
        )
        required_fields = ["Area", "Element"]
        elements = generator._filter_elements_by_fields(required_fields=required_fields)
        self.assertEqual(elements, [{"Area": "DIAG0", "Element": "GOOD"}])
