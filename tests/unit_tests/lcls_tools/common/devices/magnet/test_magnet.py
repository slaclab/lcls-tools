#!/usr/local/lcls/package/python/current/bin/python

# Built in
from unittest import TestCase
from unittest.mock import Mock, patch, PropertyMock
import inspect

# Local imports
from lcls_tools.common.devices.magnet.reader import create_magnet
from lcls_tools.common.devices.magnet.magnet import MagnetCollection


class MagnetTest(TestCase):
    """All these tests rely on EPICS functioning as we expect,
    but we have not testing framework for EPICS code, fun!
    """

    def setUp(self) -> None:
        # Set up some mocks that are needed for all test-cases.
        self.options_and_getter_function = {
            "TRIM": None,
            "PERTURB": None,
            "BCON_TO_BDES": None,
            "SAVE_BDES": None,
            "LOAD_BDES": None,
            "UNDO_BDES": None,
            "DAC_ZERO": None,
            "CALIB": None,
            "STDZ": None,
            "RESET": None,
            "TURN_OFF": None,
            "TURN_ON": None,
            "DEGAUSS": None,
        }
        self.ctrl_options_patch = patch("epics.PV.get_ctrlvars", new_callable=Mock)
        self.mock_ctrl_options = self.ctrl_options_patch.start()
        self.mock_ctrl_options.return_value = {
            "enum_strs": tuple(self.options_and_getter_function.keys())
        }
        self.magnet = create_magnet(
            area="GUNB",
            name="SOL1B",
        )
        # Set up some variables that are used by several test-cases
        self.options_requiring_state_check = [
            "TRIM",
            "PERTURB",
            "DAC_ZERO",
            "CALIB",
            "STDZ",
        ]
        self.options_and_getter_function = {
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
            "TURN_OFF": self.magnet.turn_off,
            "TURN_ON": self.magnet.turn_on,
            "DEGAUSS": self.magnet.degauss,
        }
        return super().setUp()

    def tearDown(self) -> None:
        # Stop the shared patches after each test-case is complete.
        self.ctrl_options_patch.stop()
        return super().tearDown()

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
        self.assertEqual(inspect.ismethod(self.magnet.turn_off), True)
        self.assertEqual(inspect.ismethod(self.magnet.turn_on), True)
        self.assertEqual(inspect.ismethod(self.magnet.degauss), True)
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

    @patch("epics.PV.put", new_callable=Mock)
    def test_set_bdes(self, mock_pv_put):
        mock_pv_put.return_value = None
        self.magnet.bdes = 0.1
        mock_pv_put.assert_called_once_with(value=0.1)

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
        self.mock_ctrl_options.return_value = {
            "enum_strs": tuple(self.options_and_getter_function.keys()),
        }
        for option, func in self.options_and_getter_function.items():
            func()
            pv_put_mock.assert_called_once_with(self.magnet.ctrl_options[option])
            pv_put_mock.reset_mock()

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_control_functions_that_do_nothing_if_not_ready(
        self, mock_ctrl, pv_put_mock
    ):
        mock_ctrl.return_value = "Not Ready"
        self.mock_ctrl_options.return_value = {
            "enum_strs": tuple(self.options_and_getter_function.keys()),
        }

        for option, func in self.options_and_getter_function.items():
            func()
            if option in self.options_requiring_state_check:
                pv_put_mock.assert_not_called()
            else:
                pv_put_mock.assert_called_once_with(self.magnet.ctrl_options[option])
            pv_put_mock.reset_mock()

    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.bdes",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.bact",
        new_callable=PropertyMock,
    )
    def test_bact_is_settled(self, mock_bact, mock_bdes):
        mock_bact.return_value = 0.001
        mock_bdes.return_value = 0.0009
        self.assertTrue(self.magnet.is_bact_settled(b_tolerance=0.0002))

    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.bdes",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.bact",
        new_callable=PropertyMock,
    )
    def test_bact_is_not_settled(self, mock_bact, mock_bdes):
        mock_bact.return_value = 0.001
        mock_bdes.return_value = 0.01
        self.assertFalse(self.magnet.is_bact_settled(b_tolerance=0.001))

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.magnet.magnet.MagnetControlInformation.ctrl_options",
        new_callable=PropertyMock,
    )
    def test_nothing_happens_if_ctrl_option_is_not_available(
        self, mock_ctrl_options, mock_ctrl, mock_put
    ):
        mock_ctrl_options.return_value = {
            "enum_strs": tuple("Ready"),
        }
        mock_ctrl.return_value = "Ready"
        for _, function in self.options_and_getter_function.items():
            function()
            mock_put.assert_not_called()
            mock_put.reset_mock()


class MagnetCollectionTest(TestCase):
    def setUp(self) -> None:
        self.options = [
            "TRIM",
            "PERTURB",
            "BCON_TO_BDES",
            "SAVE_BDES",
            "LOAD_BDES",
            "UNDO_BDES",
            "DAC_ZERO",
            "CALIB",
            "STDZ",
            "RESET",
            "TURN_OFF",
            "TURN_ON",
            "DEGAUSS",
        ]
        self.ctrl_options_patch = patch("epics.PV.get_ctrlvars", new_callable=Mock)
        self.mock_ctrl_options = self.ctrl_options_patch.start()
        self.mock_ctrl_options.return_value = {"enum_strs": tuple(self.options)}
        self.magnet_collection = create_magnet(area="GUNB")
        return super().setUp()

    def test_magnet_collection_creation(self):
        self.assertIsInstance(self.magnet_collection, MagnetCollection)

    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.bdes",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.trim",
        new_callable=Mock,
    )
    def test_set_bdes_with_no_args(self, mock_trim, mock_bdes, mock_bact_settle):
        with self.assertRaises(TypeError):
            self.magnet_collection.set_bdes()
        self.magnet_collection.set_bdes(magnet_dict={})
        mock_bdes.assert_not_called()
        mock_trim.assert_not_called()
        mock_bact_settle.assert_not_called()

    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.magnet.Magnet.trim", new_callable=Mock)
    def test_set_bdes_with_args(self, mock_trim, mock_bdes_put, mock_bact_settled):
        bdes_settings = {
            "SOL1B": 0.1,
        }
        mock_bact_settled.return_value = True
        self.magnet_collection.set_bdes(magnet_dict=bdes_settings)
        mock_bdes_put.assert_called_once_with(value=0.1)
        mock_trim.assert_called_once()
        mock_bact_settled.assert_called_once_with()

    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.magnet.Magnet.trim", new_callable=Mock)
    def test_set_bdes_with_bad_magnet_name(
        self, mock_trim, mock_bdes_put, mock_bact_settled
    ):
        bdes_settings = {
            "BAD-MAG": 0.3,
        }
        self.magnet_collection.set_bdes(magnet_dict=bdes_settings)
        mock_bdes_put.assert_not_called()
        mock_trim.assert_not_called()
        mock_bact_settled.assert_not_called()

    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.magnet.Magnet.trim", new_callable=Mock)
    def test_scan_with_no_callable(self, mock_trim, mock_put, mock_bact_settle):
        settings = [
            {
                "SOL1B": 0.1,
            },
            {
                "SOL1B": 0.15,
            },
            {
                "SOL1B": 0.2,
            },
        ]
        mock_bact_settle.return_value = True
        self.magnet_collection.scan(scan_settings=settings)
        self.assertEqual(mock_put.call_count, 3)
        self.assertEqual(mock_trim.call_count, 3)
        self.assertEqual(mock_bact_settle.call_count, 3)

    @patch(
        "lcls_tools.common.devices.magnet.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.magnet.Magnet.trim", new_callable=Mock)
    def test_scan_with_callable(self, mock_trim, mock_put, mock_bact_settle):
        mock_daq_function = Mock()
        settings = [
            {
                "SOL1B": 0.1,
            },
            {
                "SOL1B": 0.15,
            },
            {
                "SOL1B": 0.2,
            },
        ]
        mock_bact_settle.return_value = True
        self.magnet_collection.scan(scan_settings=settings, function=mock_daq_function)
        self.assertEqual(mock_put.call_count, 3)
        self.assertEqual(mock_trim.call_count, 3)
        self.assertEqual(mock_bact_settle.call_count, 3)
        self.assertEqual(mock_daq_function.call_count, 3)
