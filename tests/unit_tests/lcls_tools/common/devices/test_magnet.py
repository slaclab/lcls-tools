#!/usr/local/lcls/package/python/current/bin/python

# Built in
import datetime
from unittest import TestCase
from unittest.mock import Mock, patch, PropertyMock
import inspect

# Local imports
from lcls_tools.common.devices.reader import create_magnet
from lcls_tools.common.devices.magnet import MagnetCollection


class MagnetTest(TestCase):
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
        # set up patch so that each magnet is constructured with ALL ctrl options
        self.ctrl_options_patch = patch("epics.PV.get_ctrlvars", new_callable=Mock)
        self.mock_ctrl_options = self.ctrl_options_patch.start()
        self.mock_ctrl_options.return_value = {
            "enum_strs": tuple(self.options_and_getter_function.keys())
        }
        # create the SOL1B magnet with all possible ctrl options
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

    def test_properties_exist(self) -> None:
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
            "bmax",
            "bmin",
            #    "bdes", # is this somewhere else?
        ]:
            self.assertTrue(
                hasattr(self.magnet, item),
                msg=f"expected magnet to have attribute {item}",
            )

    def test_methods(self) -> None:
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

    def test_name(self) -> None:
        """Test we get expected default"""
        self.assertEqual(self.magnet.name, "SOL1B")

    def test_tol(self) -> None:
        """Test tol float validation"""
        self.assertIsNone(self.magnet.b_tolerance)
        self.magnet.b_tolerance = "a"
        self.assertIsNone(self.magnet.b_tolerance)
        self.magnet.b_tolerance = 1
        self.assertIsNone(self.magnet.b_tolerance)
        self.magnet.b_tolerance = 0.1
        self.assertEqual(self.magnet.b_tolerance, 0.1)

    def test_length(self) -> None:
        """Test length float validation"""
        self.assertIsNone(self.magnet.length)
        self.magnet.length = "a"
        self.assertIsNone(self.magnet.length)
        self.magnet.length = 1
        self.assertIsNone(self.magnet.length)
        self.magnet.length = 0.05
        self.assertEqual(self.magnet.length, 0.05)

    @patch("epics.PV.get", new_callable=Mock)
    def test_bact(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 0.1
        self.assertEqual(self.magnet.bact, 0.1)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_bdes(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 0.5
        self.assertEqual(self.magnet.bdes, 0.5)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.put", new_callable=Mock)
    def test_set_bdes(self, mock_pv_put) -> None:
        mock_pv_put.return_value = None
        self.magnet.bdes = 0.1
        mock_pv_put.assert_called_once_with(value=0.1)

    @patch("epics.PV.get", new_callable=Mock)
    def test_get_bctrl(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 0.5
        self.assertEqual(self.magnet.bctrl, 0.5)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_set_bctrl_with_int_and_ready(
        self,
        mock_ctrl_option,
        mock_pv_put,
    ) -> None:
        mock_ctrl_option.return_value = "Ready"
        self.magnet.bctrl = 3
        mock_pv_put.assert_called_once_with(value=3)

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_set_bctrl_with_string_and_ready(
        self,
        mock_ctrl_option,
        mock_pv_put,
    ) -> None:
        mock_ctrl_option.return_value = "Ready"
        self.magnet.bctrl = "string"
        mock_pv_put.assert_not_called()

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_set_bctrl_with_int_and_not_ready(
        self,
        mock_ctrl_option,
        mock_pv_put,
    ) -> None:
        mock_ctrl_option.return_value = "Trim"
        self.magnet.bctrl = 5
        mock_pv_put.assert_not_called()

    @patch("epics.PV.get", new_callable=Mock)
    def test_get_ctrl_calls_pv_get(self, pv_get_mock) -> None:
        pv_get_mock.return_value = "Ready"
        value = self.magnet.ctrl
        self.assertEqual(value, "Ready")
        pv_get_mock.assert_called_once_with(as_string=True)

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_control_functions_call_pv_put_if_ready(
        self, mock_ctrl_option, pv_put_mock
    ) -> None:
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
        "lcls_tools.common.devices.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    def test_control_functions_that_do_nothing_if_not_ready(
        self, mock_ctrl, pv_put_mock
    ) -> None:
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
        "lcls_tools.common.devices.magnet.Magnet.bdes",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.magnet.Magnet.bact",
        new_callable=PropertyMock,
    )
    def test_bact_is_settled(self, mock_bact, mock_bdes) -> None:
        mock_bact.return_value = 0.001
        mock_bdes.return_value = 0.0009
        self.assertTrue(self.magnet.is_bact_settled(b_tolerance=0.0002))

    @patch(
        "lcls_tools.common.devices.magnet.Magnet.bdes",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.magnet.Magnet.bact",
        new_callable=PropertyMock,
    )
    def test_bact_is_not_settled(self, mock_bact, mock_bdes) -> None:
        mock_bact.return_value = 0.001
        mock_bdes.return_value = 0.01
        self.assertFalse(self.magnet.is_bact_settled(b_tolerance=0.001))

    @patch("epics.PV.put", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.Magnet.ctrl",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.magnet.MagnetControlInformation.ctrl_options",
        new_callable=PropertyMock,
    )
    def test_nothing_happens_if_ctrl_option_is_not_available(
        self, mock_ctrl_options, mock_ctrl, mock_put
    ) -> None:
        # we now replace to all-test-case-mock that has ALL ctrl options
        # to only have 'Ready' options
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

    def test_magnet_collection_creation(self) -> None:
        self.assertIsInstance(self.magnet_collection, MagnetCollection)

    def test_seconds_since(self) -> None:
        one_second_in_the_past = datetime.datetime.now() - datetime.timedelta(seconds=1)
        time_passed = self.magnet_collection._seconds_since(
            time_to_check=one_second_in_the_past
        )
        self.assertEqual(
            time_passed,
            1,
            msg=f"Expected 1s passed, got {time_passed}s",
        )

    def test_seconds_since_throws_if_given_non_datetime_arg(self) -> None:
        time_to_check = 1000
        with self.assertRaises(TypeError):
            self.magnet_collection._seconds_since(time_to_check=time_to_check)

    @patch(
        "lcls_tools.common.devices.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch(
        "lcls_tools.common.devices.magnet.Magnet.bdes",
        new_callable=PropertyMock,
    )
    @patch(
        "lcls_tools.common.devices.magnet.Magnet.trim",
        new_callable=Mock,
    )
    def test_set_bdes_with_no_args(
        self,
        mock_trim,
        mock_bdes,
        mock_bact_settle,
    ) -> None:
        with self.assertRaises(TypeError):
            self.magnet_collection.set_bdes()
        self.magnet_collection.set_bdes(magnet_dict={})
        mock_bdes.assert_not_called()
        mock_trim.assert_not_called()
        mock_bact_settle.assert_not_called()

    @patch(
        "lcls_tools.common.devices.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.Magnet.trim", new_callable=Mock)
    def test_set_bdes_with_args(
        self,
        mock_trim,
        mock_bdes_put,
        mock_bact_settled,
    ) -> None:
        bdes_settings = {
            "SOL1B": 0.1,
        }
        mock_bact_settled.return_value = True
        self.magnet_collection.set_bdes(magnet_dict=bdes_settings)
        mock_bdes_put.assert_called_once_with(value=0.1)
        mock_trim.assert_called_once()
        mock_bact_settled.assert_called_once_with()

    @patch(
        "lcls_tools.common.devices.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.Magnet.trim", new_callable=Mock)
    def test_set_bdes_with_bad_magnet_name(
        self, mock_trim, mock_bdes_put, mock_bact_settled
    ) -> None:
        bdes_settings = {
            "BAD-MAG": 0.3,
        }
        self.magnet_collection.set_bdes(magnet_dict=bdes_settings)
        mock_bdes_put.assert_not_called()
        mock_trim.assert_not_called()
        mock_bact_settled.assert_not_called()

    @patch(
        "lcls_tools.common.devices.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.Magnet.trim", new_callable=Mock)
    def test_scan_with_no_callable(
        self,
        mock_trim,
        mock_put,
        mock_bact_settle,
    ) -> None:
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
        "lcls_tools.common.devices.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.Magnet.trim", new_callable=Mock)
    def test_scan_with_callable(
        self,
        mock_trim,
        mock_put,
        mock_bact_settle,
    ) -> None:
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

    @patch(
        "lcls_tools.common.devices.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.Magnet.trim", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.MagnetCollection._seconds_since",
        new_callable=Mock,
    )
    def test_set_bdes_when_timeout_happens(
        self, mock_timer_count, mock_trim, mock_put, mock_bact_settle
    ) -> None:
        # make sure that magnet_collection._seconds_since()
        # always returns > settle_timeout for set_bdes()
        mock_timer_count.side_effect = [6 for i in range(2)]
        # Make sure bact never settles to bdes
        mock_bact_settle.return_value = False
        settings = {
            "SOL1B": 0.1,
            "SOL2B": 0.1,
        }
        self.magnet_collection.set_bdes(settings)
        # We call functions once per-setting
        # but we ALWAYS timeout so we only call twice overall.
        self.assertEqual(mock_put.call_count, 2)
        self.assertEqual(mock_trim.call_count, 2)
        self.assertEqual(mock_bact_settle.call_count, 2)

    @patch(
        "lcls_tools.common.devices.magnet.Magnet.is_bact_settled",
        new_callable=Mock,
    )
    @patch("epics.PV.put", new_callable=Mock)
    @patch("lcls_tools.common.devices.magnet.Magnet.trim", new_callable=Mock)
    @patch(
        "lcls_tools.common.devices.magnet.MagnetCollection._seconds_since",
        new_callable=Mock,
    )
    def test_set_bdes_when_timeout_happens_after_first_call(
        self, mock_timer_count, mock_trim, mock_put, mock_bact_settle
    ) -> None:
        # make sure that magnet_collection._seconds_since()
        # always returns > settle_timeout for set_bdes()
        mock_timer_count.side_effect = [i + 4 for i in range(10)]
        # Make sure bact never settles to bdes
        mock_bact_settle.return_value = False
        settings = {
            "SOL1B": 0.1,
        }
        self.magnet_collection.set_bdes(settings)
        # We call functions once per-setting
        # but we ALWAYS timeout so we only call once overall.
        self.assertEqual(mock_put.call_count, 1)
        self.assertEqual(mock_trim.call_count, 1)
        # We will call the bact_settle function 3 times
        # 1st (0 + 4 secs) !>  5, 2nd (1 + 4 secs) !> 5, 3rd (2 + 4secs) > 5
        self.assertEqual(mock_bact_settle.call_count, 3)

    @patch("lcls_tools.common.devices.magnet.Magnet.turn_off", new_callable=Mock)
    def test_turn_off_single_magnet(self, mock_turn_off):
        magnet_name = "SOL1B"
        self.magnet_collection.turn_off(magnet_name)
        mock_turn_off.assert_called_once()

    @patch("lcls_tools.common.devices.magnet.Magnet.turn_off", new_callable=Mock)
    def test_turn_off_multiple_magnets(self, mock_turn_off):
        magnet_names = ["SOL1B", "SOL2B"]
        self.magnet_collection.turn_off(magnet_names)
        self.assertEqual(mock_turn_off.call_count, 2)

    @patch("lcls_tools.common.devices.magnet.Magnet.turn_off", new_callable=Mock)
    def test_turn_off_all_magnets(self, mock_turn_off):
        self.magnet_collection.turn_off()
        total_number_of_magnets = len(self.magnet_collection.magnets)
        self.assertEqual(mock_turn_off.call_count, total_number_of_magnets)

    @patch("lcls_tools.common.devices.magnet.Magnet.turn_off", new_callable=Mock)
    def test_turn_off_bad_magnet(self, mock_turn_off):
        magnet_name = "BAD-MAGNET"
        self.magnet_collection.turn_off(magnet_name)
        mock_turn_off.assert_not_called()

    @patch("lcls_tools.common.devices.magnet.Magnet.turn_on", new_callable=Mock)
    def test_turn_on_single_magnet(self, mock_turn_on):
        magnet_name = "SOL1B"
        self.magnet_collection.turn_on(magnet_name)
        mock_turn_on.assert_called_once()

    @patch("lcls_tools.common.devices.magnet.Magnet.turn_on", new_callable=Mock)
    def test_turn_on_multiple_magnets(self, mock_turn_on):
        magnet_names = ["SOL1B", "SOL2B"]
        self.magnet_collection.turn_on(magnet_names)
        self.assertEqual(mock_turn_on.call_count, 2)

    @patch("lcls_tools.common.devices.magnet.Magnet.turn_on", new_callable=Mock)
    def test_turn_on_all_magnets(self, mock_turn_on):
        self.magnet_collection.turn_on()
        total_number_of_magnets = len(self.magnet_collection.magnets)
        self.assertEqual(mock_turn_on.call_count, total_number_of_magnets)

    @patch("lcls_tools.common.devices.magnet.Magnet.turn_on", new_callable=Mock)
    def test_turn_on_bad_magnet(self, mock_turn_on):
        magnet_name = "BAD-MAGNET"
        self.magnet_collection.turn_on(magnet_name)
        mock_turn_on.assert_not_called()

    @patch("lcls_tools.common.devices.magnet.Magnet.turn_on", new_callable=Mock)
    def test_degauss_single_magnet(self, mock_turn_on):
        magnet_name = "SOL1B"
        self.magnet_collection.turn_on(magnet_name)
        mock_turn_on.assert_called_once()

    @patch("lcls_tools.common.devices.magnet.Magnet.degauss", new_callable=Mock)
    def test_degauss_multiple_magnets(self, mock_degauss):
        magnet_names = ["SOL1B", "SOL2B"]
        self.magnet_collection.degauss(magnet_names)
        self.assertEqual(mock_degauss.call_count, 2)

    @patch("lcls_tools.common.devices.magnet.Magnet.degauss", new_callable=Mock)
    def test_degauss_all_magnets(self, mock_degauss):
        self.magnet_collection.degauss()
        total_number_of_magnets = len(self.magnet_collection.magnets)
        self.assertEqual(mock_degauss.call_count, total_number_of_magnets)

    @patch("lcls_tools.common.devices.magnet.Magnet.degauss", new_callable=Mock)
    def test_degauss_bad_magnet(self, mock_degauss):
        magnet_name = "BAD-MAGNET"
        self.magnet_collection.degauss(magnet_name)
        mock_degauss.assert_not_called()
