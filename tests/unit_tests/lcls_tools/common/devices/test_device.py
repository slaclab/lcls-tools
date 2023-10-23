import os
import unittest
from unittest.mock import MagicMock, patch
from lcls_tools.common.devices.device import (
    Device,
    ApplyDeviceCallbackError,
    RemoveDeviceCallbackError,
    MandatoryFieldNotFoundInYAMLError,
)
from epics import PV
import yaml


class TestDevice(unittest.TestCase):
    def setUp(self) -> None:
        self.config_location = "./tests/datasets/devices/config/"
        self.config_filename = os.path.join(self.config_location, "base_device.yaml")
        with open(self.config_filename, "r") as file:
            self.device_name = "DEVICE_1"
            self.config_data = yaml.safe_load(file)
            self.device = Device(
                name=self.device_name, config=self.config_data[self.device_name]
            )
        self.pv_obj = PV("SOLN:GUNB:212:BACT")
        return super().setUp()

    def test_config_with_no_control_information_field_raises(self):
        name_of_device_with_missing_data = "DEVICE_2"
        with self.assertRaises(MandatoryFieldNotFoundInYAMLError):
            Device(
                name=name_of_device_with_missing_data,
                config=self.config_data[name_of_device_with_missing_data],
            )

    def test_config_with_no_metadata_field_raises(self):
        name_of_device_with_missing_data = "DEVICE_3"
        with self.assertRaises(MandatoryFieldNotFoundInYAMLError):
            Device(
                name=name_of_device_with_missing_data,
                config=self.config_data[name_of_device_with_missing_data],
            )

    def test_properties_exist(self):
        """Test that all the properties we expect exist"""
        # Assert that device has all auto-generated private attributes
        for item in self.device._mandatory_fields:
            self.assertTrue(
                hasattr(self.device, item),
                msg=f"expected device to have attribute {item}",
            )

    def test_name_property_assigned_after_init(self):
        self.assertEqual(self.device.name, self.device_name)

    @patch(
        "lcls_tools.common.devices.device.Device._get_attribute",
        new_callable=MagicMock(),
    )
    def test_get_pv_object_from_str_with_good_pv_string(
        self,
        mock_get_attribute: MagicMock,
    ) -> None:
        good_pv_name = "SOLN:GUNB:212:BCTRL"
        good_pv_obj = PV(good_pv_name)
        mock_get_attribute.return_value = good_pv_obj
        result = self.device._get_pv_object_from_str("bact")
        self.assertIsNotNone(result)
        self.assertEqual(result, good_pv_obj)

    def test_get_pv_object_from_str_with_bad_pv_string(self):
        result = self.device._get_pv_object_from_str("bad-name")
        self.assertIsNone(result)

    @patch(
        "lcls_tools.common.devices.device.Device._get_attribute",
        new_callable=MagicMock(),
    )
    def test_get_callbacks_with_good_pv_string(
        self,
        mock_get_attribute: MagicMock,
    ) -> None:
        good_pv_name = "SOLN:GUNB:212:BCTRL"
        good_pv_obj = PV(good_pv_name)
        handle = "bact"
        mock_get_attribute.return_value = good_pv_obj
        result = self.device.get_callbacks(handle)
        self.assertIsNotNone(result)
        # start with empty dictionary check
        self.assertEqual(result, dict())

        def dummy_callback():
            print("test callback")

        # add some callback function to the pv
        self.device.add_callback_to_pv(pv=handle, function=dummy_callback)
        result = self.device.get_callbacks(handle)
        # check we have an indexed-dictionary of callback functions
        expected_callback_structure = {1: (dummy_callback, {})}
        self.assertEqual(result, expected_callback_structure)

    def test_get_callbacks_with_bad_pv_string(self):
        result = self.device.get_callbacks("bad-pv-handle")
        self.assertIsNone(result)

    def test_get_callback_index_with_no_callbacks_for_pv(self):
        mock_pv = self.pv_obj

        def mock_callback():
            print("mock callback")

        index = self.device._get_callback_index(mock_pv, mock_callback)
        self.assertIsNone(index)

    @patch(
        "lcls_tools.common.devices.device.Device._get_attribute",
        new_callable=MagicMock(),
    )
    def test_get_callback_index_with_multiple_callbacks_for_pv(
        self,
        mock_get_attribute: MagicMock,
    ) -> None:
        mock_pv = self.pv_obj
        mock_get_attribute.return_value = mock_pv

        def mock_callback(message: str) -> None:
            print(f"callback: {message}")

        # Add different callbacks to Device
        def first_callback():
            mock_callback("first")

        def second_callback():
            mock_callback("second")

        def third_callback():
            mock_callback("third")

        self.device.add_callback_to_pv(
            "bact",
            first_callback,
        )
        self.device.add_callback_to_pv(
            "bact",
            second_callback,
        )
        self.device.add_callback_to_pv(
            "bact",
            third_callback,
        )
        # Retrieve the index of 2nd callback function
        # Annoying because PV callback indexes start from 1.
        index = self.device._get_callback_index(
            mock_pv,
            second_callback,
        )
        # Check that index is 2 because we asked for 2nd callback
        self.assertEqual(index, 2)

    def test_add_callback_to_pv_raises_with_bad_pv_arg(self):
        with self.assertRaises(ApplyDeviceCallbackError):

            def mock_callback():
                pass

            self.device.add_callback_to_pv(
                pv=self.pv_obj,
                function=mock_callback,
            )

    def test_add_callback_to_pv_raises_with_bad_callback_arg(self):
        with self.assertRaises(ApplyDeviceCallbackError):
            self.device.add_callback_to_pv(
                pv="bact",
                function=dict(),
            )

    def test_add_callback_raises_when_pv_does_not_exist(self):
        def mock_callback():
            pass

        with self.assertRaises(ApplyDeviceCallbackError):
            self.device.add_callback_to_pv(pv="bact", function=mock_callback)

    @patch(
        "lcls_tools.common.devices.device.Device._get_attribute",
        new_callable=MagicMock(),
    )
    def test_add_callback_raises_when_callback_exists_for_pv(
        self,
        mock_get_attribute: MagicMock,
    ) -> None:
        def mock_callback():
            pass

        mock_get_attribute.return_value = self.pv_obj
        self.pv_obj.add_callback(mock_callback)
        with self.assertRaises(ApplyDeviceCallbackError):
            self.device.add_callback_to_pv(pv="bact", function=mock_callback)

    @patch(
        "lcls_tools.common.devices.device.Device._get_attribute",
        new_callable=MagicMock(),
    )
    def test_add_callback_success_when_callback_new_for_pv(
        self,
        mock_get_attribute: MagicMock,
    ) -> None:
        def mock_callback():
            pass

        mock_get_attribute.return_value = self.pv_obj
        self.assertEqual(len(self.pv_obj.callbacks), 0)
        self.device.add_callback_to_pv(pv="bact", function=mock_callback)
        # Check we added the callback
        self.assertNotEqual(len(self.pv_obj.callbacks), 0)
        expected_callback_structure = {1: (mock_callback, {})}
        # Check callbacks come back as expected
        self.assertEqual(self.pv_obj.callbacks, expected_callback_structure)

    def test_remove_callback_to_pv_raises_with_bad_pv_arg(self):
        with self.assertRaises(RemoveDeviceCallbackError):

            def mock_callback():
                pass

            self.device.remove_callback_from_pv(
                pv=self.pv_obj,
                function=mock_callback,
            )

    def test_remove_callback_to_pv_raises_with_bad_callback_arg(self):
        with self.assertRaises(RemoveDeviceCallbackError):
            self.device.remove_callback_from_pv(
                pv="bact",
                function=dict(),
            )

    def test_remove_callback_raises_when_pv_does_not_exist(self):
        def mock_callback():
            pass

        with self.assertRaises(RemoveDeviceCallbackError):
            self.device.remove_callback_from_pv(pv="bact", function=mock_callback)

    @patch(
        "lcls_tools.common.devices.device.Device._get_attribute",
        new_callable=MagicMock(),
    )
    def test_remove_callback_raises_when_callback_does_not_exist_for_pv(
        self,
        mock_get_attribute: MagicMock,
    ) -> None:
        def mock_callback():
            pass

        mock_get_attribute.return_value = self.pv_obj
        with self.assertRaises(RemoveDeviceCallbackError):
            self.device.remove_callback_from_pv(pv="bact", function=mock_callback)

    @patch(
        "lcls_tools.common.devices.device.Device._get_attribute",
        new_callable=MagicMock(),
    )
    def test_remove_callback_success_when_callback_exists_for_pv(
        self,
        mock_get_attribute: MagicMock,
    ) -> None:
        def mock_callback():
            pass

        mock_get_attribute.return_value = self.pv_obj
        self.pv_obj.add_callback(mock_callback)
        self.assertEqual(len(self.pv_obj.callbacks), 1)
        expected_callback_structure = {1: (mock_callback, {})}
        # Check that we have added the callback
        self.assertEqual(self.pv_obj.callbacks, expected_callback_structure)
        # Check that we don't throw error when removing callback
        self.device.remove_callback_from_pv("bact", mock_callback)
        # Check callback has been removed
        self.assertEqual(len(self.pv_obj.callbacks), 0)
        self.assertEqual(self.pv_obj.callbacks, {})
