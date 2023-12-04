# Built in
from unittest import mock, TestCase
import inspect

# Local imports
import lcls_tools.common.devices.profmon_constants as pc
from lcls_tools.common.devices.profile_monitor import (
    ProfMon,
    get_profile_monitors,
)


PROF = {
    "set": "test:PNEUMATIC",
    "get": "test:TGT_STS",
    "image": "test:IMAGE",
    "res": "test:RESOLUTION",
    "xsize": "test:N_OF_COL",
    "ysize": "test:N_OF_ROW",
    "rate": "test:FRAME_RATE",
}

PROF2 = {
    "set": "test:PNEUMATIC",
    "get": "test:TGT_STS",
    "image": "test:Image:ArrayData",
    "res": "test:RESOLUTION",
    "xsize": "test:ArraySizeX_RBV",
    "ysize": "test:ArraySizeY_RBV",
    "rate": "test:FRAME_RATE",
}

PROFS = ["OTR02", "YAG01B", "YAG01"]


class ProfileMonitorTest(TestCase):
    ############ Constants ############

    def test_create_profmon_dict(self):
        """Typical LCLS style PV naming convention"""
        self.assertEqual(pc.create_profmon_dict("test"), PROF)

    def test_create_profmon2_dict(self):
        """New LCLS2 style PV naming convention"""
        self.assertEqual(pc.create_profmon2_dict("test"), PROF2)

    def test_get_profile_monitors(self):
        """To verify we haven't added any profs"""
        self.assertEqual(get_profile_monitors(), sorted(PROFS))

    ############# Object ##############
    @mock.patch("epics.PV.get", new_callable=mock.Mock)
    @mock.patch("epics.PV.get_ctrlvars", new_callable=mock.Mock)
    def test_properties(self, mock_get_ctrl_vars, mock_pv_get):
        """Test that all the properties we expect exist"""
        mock_get_ctrl_vars.return_value = {"enum_strs": ["IN"]}
        mock_pv_get.return_value = 0
        p = ProfMon()
        self.assertEqual(isinstance(type(p).prof_name, property), True)
        self.assertEqual(isinstance(type(p).cur_image, property), True)
        self.assertEqual(isinstance(type(p).saved_images, property), True)
        self.assertEqual(isinstance(type(p).resolution, property), True)
        self.assertEqual(isinstance(type(p).arr_dims, property), True)
        self.assertEqual(isinstance(type(p).rate, property), True)
        self.assertEqual(isinstance(type(p).motion_state, property), True)
        self.assertEqual(isinstance(type(p).state, property), True)

    @mock.patch("epics.PV.get", new_callable=mock.Mock)
    @mock.patch("epics.PV.get_ctrlvars", new_callable=mock.Mock)
    def test_methods(self, mock_get_ctrl_vars, mock_pv_get):
        """Test that all the methods we expect exist"""
        mock_get_ctrl_vars.return_value = {"enum_strs": ["IN"]}
        mock_pv_get.return_value = 0
        p = ProfMon()
        self.assertEqual(inspect.ismethod(p.insert), True)
        self.assertEqual(inspect.ismethod(p._inserted), True)
        self.assertEqual(inspect.ismethod(p.extract), True)
        self.assertEqual(inspect.ismethod(p._extracted), True)
        self.assertEqual(inspect.ismethod(p.acquire_images), True)
        self.assertEqual(inspect.ismethod(p._collect_image_data), True)

    @mock.patch("epics.PV.get", new_callable=mock.Mock)
    @mock.patch("epics.PV.get_ctrlvars", new_callable=mock.Mock)
    def test_name(self, mock_get_ctrl_vars, mock_pv_get):
        """Test that we get default name and can hand name in init arg"""
        mock_get_ctrl_vars.return_value = {"enum_strs": ["IN"]}
        mock_pv_get.return_value = 0
        p = ProfMon()
        self.assertEqual(p.prof_name, "OTR02")
        p = ProfMon("YAG01")
        self.assertEqual(p.prof_name, "YAG01")
