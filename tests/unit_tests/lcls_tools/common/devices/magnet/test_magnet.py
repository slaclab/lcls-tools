#!/usr/local/lcls/package/python/current/bin/python

# Built in
from unittest import TestCase
from unittest.mock import Mock, patch, PropertyMock
import inspect

# Local imports
from lcls_tools.common.devices.magnet.reader import create_magnet


class MagnetTest(TestCase):
    """All these tests rely on EPICS functioning as we expect,
    but we have not testing framework for EPICS code, fun!
    """

    def setUp(self) -> None:
        self.magnet = create_magnet(
            area="GUNB",
            # "./tests/datasets/devices/config/magnet/typical_magnet.yaml",
            name="SOL1B",
        )
        return super().setUp()

    def test_properties_exist(self):
        """Test that all the properties we expect exist"""
        # Assert that magnet has all auto-generated private attributes
        for handle, _ in self.magnet.controls_information.PVs:
            self.assertTrue(
                hasattr(self.magnet, handle),
                msg=f"expected magnet to have attribute {handle}",
            )
        for item, _ in self.magnet.metadata:
            self.assertTrue(
                hasattr(self.magnet, item),
                msg=f"expected magnet to have attribute {item}",
            )
        # Assert that magnet has public properties
        for item in [
            "bctrl",
            "bact",
            "ctrl",
            "length",
            "b_tolerance",
        ]:
            self.assertTrue(
                hasattr(self.magnet, item),
                msg=f"expected magnet to have attribute {item}",
            )

    def test_methods(self):
        """Test that all the methods we expect exist"""
        self.assertEqual(inspect.ismethod(self.magnet.trim), True)
        self.assertEqual(inspect.ismethod(self.magnet.perturb), True)
        self.assertEqual(inspect.ismethod(self.magnet.con_to_des), True)
        self.assertEqual(inspect.ismethod(self.magnet.save_bdes), True)
        self.assertEqual(inspect.ismethod(self.magnet.load_bdes), True)
        self.assertEqual(inspect.ismethod(self.magnet.undo_bdes), True)
        self.assertEqual(inspect.ismethod(self.magnet.dac_zero), True)
        self.assertEqual(inspect.ismethod(self.magnet.calibrate), True)
        self.assertEqual(inspect.ismethod(self.magnet.standardize), True)
        self.assertEqual(inspect.ismethod(self.magnet.reset), True)
        self.assertEqual(inspect.ismethod(self.magnet.add_callback_to_pv), True)
        self.assertEqual(inspect.ismethod(self.magnet.remove_callback_from_pv), True)

    def test_name(self):
        """Test we get expected default"""
        self.assertEqual(self.magnet.name, "SOL1B")

    def test_tol(self):
        """Test tol float validation"""
        self.assertIsNone(self.magnet.b_tolerance)
        self.magnet.b_tolerance = "a"
        self.assertIsNone(self.magnet.b_tolerance)
        self.magnet.b_tolerance = 1
        self.assertIsNone(self.magnet.b_tolerance)
        self.magnet.b_tolerance = 0.1
        self.assertEqual(self.magnet.b_tolerance, 0.1)

    def test_length(self):
        """Test length float validation"""
        self.assertIsNone(self.magnet.length)
        self.magnet.length = "a"
        self.assertIsNone(self.magnet.length)
        self.magnet.length = 1
        self.assertIsNone(self.magnet.length)
        self.magnet.length = 0.05
        self.assertEqual(self.magnet.length, 0.05)

    @patch("epics.PV.get", new_callable=Mock)
    def test_bact(self, mock_pv_get):
        mock_pv_get.return_value = 0.1
        self.assertEqual(self.magnet.bact, 0.1)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_bdes(self, mock_pv_get):
        mock_pv_get.return_value = 0.5
        self.assertEqual(self.magnet.bdes, 0.5)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_get_bctrl(self, mock_pv_get):
        mock_pv_get.return_value = 0.5
        self.assertEqual(self.magnet.bctrl, 0.5)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_set_bctrl_with_int_and_ready(self, mock_ctrl_option, mock_pv_put):
        mock_ctrl_option.return_value = "Ready"
        self.magnet.bctrl = 3
        mock_pv_put.assert_called_once_with(value=3)

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_set_bctrl_with_string_and_ready(self, mock_ctrl_option, mock_pv_put):
        mock_ctrl_option.return_value = "Ready"
        self.magnet.bctrl = "string"
        mock_pv_put.assert_not_called()

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_set_bctrl_with_int_and_not_ready(self, mock_ctrl_option, mock_pv_put):
        mock_ctrl_option.return_value = "Trim"
        self.magnet.bctrl = 5
        mock_pv_put.assert_not_called()

    @patch("epics.PV.get", new_callable=Mock)
    def test_get_ctrl_calls_pv_get(self, pv_get_mock):
        pv_get_mock.return_value = "Ready"
        value = self.magnet.ctrl
        self.assertEqual(value, "Ready")
        pv_get_mock.assert_called_once_with(as_string=True)

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_control_functions_call_pv_put_if_ready(
        self, mock_ctrl_option, pv_put_mock
    ):
        mock_ctrl_option.return_value = "Ready"
        options_and_getter_function = {
            "TRIM": self.magnet.trim,
            "PERTURB": self.magnet.perturb,
            "BCON_TO_BDES": self.magnet.con_to_des,
            "SAVE_BDES": self.magnet.save_bdes,
            "LOAD_BDES": self.magnet.load_bdes,
            "UNDO_BDES": self.magnet.undo_bdes,
            "DAC_ZERO": self.magnet.dac_zero,
            "CALIB": self.magnet.calibrate,
            "STDZ": self.magnet.standardize,
            "RESET": self.magnet.reset,
        }
        for option, func in options_and_getter_function.items():
            func()
            pv_put_mock.assert_called_once_with(self.magnet.ctrl_options[option])
            pv_put_mock.reset_mock()

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_trim_does_nothing_if_not_ready(self, mock_ctrl_option, pv_put_mock):
        mock_ctrl_option.return_value = "Not Ready"
        options_and_getter_function = {
            "TRIM": self.magnet.trim,
            "PERTURB": self.magnet.perturb,
            "BCON_TO_BDES": self.magnet.con_to_des,
            "SAVE_BDES": self.magnet.save_bdes,
            "LOAD_BDES": self.magnet.load_bdes,
            "UNDO_BDES": self.magnet.undo_bdes,
            "DAC_ZERO": self.magnet.dac_zero,
            "CALIB": self.magnet.calibrate,
            "STDZ": self.magnet.standardize,
            "RESET": self.magnet.reset,
        }
        options_requiring_state_check = [
            "TRIM",
            "PERTURB",
            "DAC_ZERO",
            "CALIB",
            "STDZ",
        ]
        for option, func in options_and_getter_function.items():
            func()
            if option in options_requiring_state_check:
                pv_put_mock.assert_not_called()
            else:
                pv_put_mock.assert_called_once_with(self.magnet.ctrl_options[option])
            pv_put_mock.reset_mock()
