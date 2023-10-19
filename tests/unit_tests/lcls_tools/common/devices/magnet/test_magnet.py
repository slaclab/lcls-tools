#!/usr/local/lcls/package/python/current/bin/python

# Built in
from unittest import TestCase
from unittest.mock import Mock, patch
import inspect

# Local imports
from lcls_tools.common.devices.magnet.reader import create_magnet


class MagnetTest(TestCase):
    """All these tests rely on EPICS functioning as we expect,
    but we have not testing framework for EPICS code, fun!
    """

    def setUp(self) -> None:
        self.magnet = create_magnet(
            "./tests/datasets/devices/config/magnet/typical_magnet.yaml",
            name="SOL1B",
        )
        return super().setUp()

    ########### Magnet object ###########

    def test_missing_mandatory_pv_raises_attribute_error(self):
        with self.assertRaises(AttributeError):
            self.bad_magnet = create_magnet(
                "./tests/datasets/devices/config/magnet/missing_pv_magnet.yaml",
                name="SOL2B",
            )

    def test_properties_exist(self):
        """Test that all the properties we expect exist"""
        # Assert that magnet has all auto-generated private attributes
        for item in self.magnet._mandatory_pvs:
            self.assertTrue(
                hasattr(self.magnet, "_" + item),
                msg=f"expected magnet to have attribute {item}",
            )
        for item in self.magnet.metadata:
            self.assertTrue(
                hasattr(self.magnet, "_" + item),
                msg=f"expected magnet to have attribute {item}",
            )
        # Assert that magnet has public properties
        for item in [
            "bctrl",
            "bact",
            "ctrl_value",
            "length",
            "b_tolerance",
        ]:
            self.assertTrue(
                hasattr(self.magnet, "bctrl"),
                msg=f"expected magnet to have attribute {item}",
            )

        for item in self.magnet._mandatory_fields:
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
        self.assertEqual(self.magnet.b_tolerance, 0.002)
        self.magnet.b_tolerance = "a"
        self.assertEqual(self.magnet.b_tolerance, 0.002)
        self.magnet.b_tolerance = 1
        self.assertEqual(self.magnet.b_tolerance, 0.002)
        self.magnet.b_tolerance = 0.1
        self.assertEqual(self.magnet.b_tolerance, 0.1)

    def test_length(self):
        """Test length float validation"""
        self.assertEqual(self.magnet.length, 0.1342)
        self.magnet.length = "a"
        self.assertEqual(self.magnet.length, 0.1342)
        self.magnet.length = 1
        self.assertEqual(self.magnet.length, 0.1342)
        self.magnet.length = 0.05
        self.assertEqual(self.magnet.length, 0.05)

    @patch('epics.PV.get', new_callable=Mock)
    def test_bact(self, mock_pv_get):
        mock_pv_get.return_value = 0.1
        self.assertEqual(self.magnet.bact, 0.1)
        mock_pv_get.assert_called_once()

    @patch('epics.PV.get', new_callable=Mock)
    def test_bdes(self, mock_pv_get):
        mock_pv_get.return_value = 0.5
        self.assertEqual(self.magnet.bdes, 0.5)
        mock_pv_get.assert_called_once()

    @patch('epics.PV.get', new_callable=Mock)
    def test_bctrl(self, mock_pv_get):
        mock_pv_get.return_value = 0.5
        self.assertEqual(self.magnet.bctrl, 0.5)
        mock_pv_get.assert_called_once()
    
    