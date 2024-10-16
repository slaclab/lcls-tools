# import datetime
from unittest import TestCase
from unittest.mock import Mock, patch  # , PropertyMock
import inspect


# Local imports
from lcls_tools.common.devices.reader import create_wire

# from lcls_tools.common.devices.wire import WireCollection


class WireTest(TestCase):
    def setUp(self) -> None:
        # Set up some mocks that are needed for all test-cases.
        self.options_and_getter_function = {
            "MOTR.VELO": None,
            "MOTR.VMAX": None,
            "MOTR.VBAS": None,
            "MOTR.RBV": None,
            "MOTR_INIT": None,
            "MOTR_INIT_STS": None,
            "MOTR_RETRACT": None,
            "MOTR": None,
            "STARTSCAN": None,
            "USEXWIRE": None,
            "USEYWIRE": None,
            "USEUWIRE": None,
            "XWIREINNER": None,
            "XWIREOUTER": None,
            "YWIREINNER": None,
            "YWIREOUTER": None,
            "UWIREINNER": None,
            "UWIREOUTER": None,
            "MOTR_ENABLED_STS": None,
            "MOTR_HOMED_STS": None,
        }
        # set up patch so that each magnet is constructured with ALL ctrl options
        self.ctrl_options_patch = patch("epics.PV.get_ctrlvars", new_callable=Mock)
        self.mock_ctrl_options = self.ctrl_options_patch.start()
        self.mock_ctrl_options.return_value = {
            "enum_strs": tuple(self.options_and_getter_function.keys())
        }
        # create the WSBP2 wire with all possible ctrl options
        self.wire = create_wire(
            area="BYP",
            name="WSBP2",
        )
        self.options_requiring_state_check = [
            "MOTR",
        ]
        self.options_and_getter_function = {
            "MOTR.STOP": self.wire.abort_scan,
            "MOTR_ENABLED_STS": self.wire.enabled,
            "MOTR_HOMED_STS": self.wire.homed,
            "MOTR_INIT": self.wire.initialize,
            "MOTR_INIT_STS": self.wire.initialize_status,
            "MOTR": self.wire.motor,
            "MOTR.RBV": self.wire.position,
            "MOTR_RETRACT": self.wire.retract,
            "SCANPULSES": self.wire.scan_pulses,
            "MOTR.VELO": self.wire.speed,
            "MOTR.VMAX": self.wire.speed_max,
            "MOTR.VBAS": self.wire.speed_min,
            "STARTSCAN": self.wire.start_scan,
            "TEMP": self.wire.temperature,
            "MOTR_TIMEOUTEN": self.wire.timeout,
            "USEUWIRE": self.wire.use_u_wire,
            "USEXWIRE": self.wire.use_x_wire,
            "USEYWIRE": self.wire.use_y_wire,
            "UWIRESIZE": self.wire.u_size,
            "UWIREINNER": self.wire.u_wire_inner,
            "UWIREOUTER": self.wire.u_wire_outer,
            "XWIREINNER": self.wire.x_wire_inner,
            "XWIREOUTER": self.wire.x_wire_outer,
            "XWIRESIZE": self.wire.x_size,
            "YWIREINNER": self.wire.y_wire_inner,
            "YWIREOUTER": self.wire.y_wire_outer,
            "YWIRESIZE": self.wire.y_size,
        }
        return super().setUp()

    def tearDown(self) -> None:
        # Stop the shared patches after each test-case is complete.
        self.ctrl_options_patch.stop()
        return super().tearDown()

    def test_properties_exist(self) -> None:
        """Test that all the properties we expect exist"""
        # Assert that wire has all auto-generated private attributes
        for handle, _ in self.wire.controls_information.PVs:
            if handle not in ["position",]:
                self.assertTrue(
                    hasattr(self.wire, handle),
                    msg=f"expected wire to have attribute {handle}",
                )
        for item, _ in self.wire.metadata:
            self.assertTrue(
                hasattr(self.wire, item),
                msg=f"expected wire to have attribute {item}",
            )
        # Assert that magnet has public properties
        for item in [
            "abort_scan",
            "enabled",
            "homed",
            "initialize",
            "initialize_status",
            "motor",
            "position",
            "retract",
            "scan_pulses",
            "speed",
            "start_scan",
            "temperature",
            "timeout",
            "use_u_wire",
            "use_x_wire",
            "use_y_wire",
            "u_size",
            "u_wire_inner",
            "u_wire_outer",
            "x_wire_inner",
            "x_wire_outer",
            "x_size",
            "y_wire_inner",
            "y_wire_outer",
            "y_size",
        ]:
            self.assertTrue(
                hasattr(self.wire, item),
                msg=f"expected wire to have attribute {item}",
            )

    def test_methods(self) -> None:
        """Test that all the methods we expect exist"""
        self.assertEqual(inspect.ismethod(self.wire.retract), True)
        self.assertEqual(inspect.ismethod(self.wire.start_scan), True)
        self.assertEqual(inspect.ismethod(self.wire.abort_scan), True)
        self.assertEqual(inspect.ismethod(self.wire.initialize), True)
        self.assertEqual(inspect.ismethod(self.wire.set_inner_range), True)
        self.assertEqual(inspect.ismethod(self.wire.set_outer_range), True)
        self.assertEqual(inspect.ismethod(self.wire.set_range), True)
        self.assertEqual(inspect.ismethod(self.wire.use), True)

    def test_name(self) -> None:
        """Test we get expected default"""
        self.assertEqual(self.wire.name, "WSBP2")

    @patch("epics.PV.get", new_callable=Mock)
    def test_use_x_wire(self, mock_pv_get) -> None:
        """Test use x wire validation"""
        mock_pv_get.return_value = 1
        self.assertEqual(self.wire.use_x_wire, 1)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_use_y_wire(self, mock_pv_get) -> None:
        """Test use y wire validation"""
        mock_pv_get.return_value = 1
        self.assertEqual(self.wire.use_y_wire, 1)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_use_u_wire(self, mock_pv_get) -> None:
        """Test use u wire validation"""
        mock_pv_get.return_value = 1
        self.assertEqual(self.wire.use_u_wire, 1)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_position(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 10000
        self.assertEqual(self.wire.position, 10000)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_u_size(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 10
        self.assertEqual(self.wire.u_size, 10)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_x_size(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 10
        self.assertEqual(self.wire.x_size, 10)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_y_size(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 10
        self.assertEqual(self.wire.y_size, 10)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_u_wire_inner(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 9000
        self.assertEqual(self.wire.u_wire_inner, 9000)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_u_wire_outer(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 14000
        self.assertEqual(self.wire.u_wire_inner, 14000)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_x_wire_inner(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 9000
        self.assertEqual(self.wire.x_wire_inner, 9000)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_x_wire_outer(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 14000
        self.assertEqual(self.wire.x_wire_inner, 14000)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_y_wire_inner(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 9000
        self.assertEqual(self.wire.y_wire_inner, 9000)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_y_wire_outer(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 14000
        self.assertEqual(self.wire.y_wire_inner, 14000)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_initialize_status(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 1
        self.assertEqual(self.wire.initialize_status, 1)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_homed(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 1
        self.assertEqual(self.wire.homed, 1)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_speed(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 30000
        self.assertEqual(self.wire.speed, 30000)
        mock_pv_get.assert_called_once()

    @patch("epics.PV.get", new_callable=Mock)
    def test_scan_pulses(self, mock_pv_get) -> None:
        mock_pv_get.return_value = 350
        self.assertEqual(self.wire.scan_pulses, 350)
        mock_pv_get.assert_called_once()

    def test_all(self) -> None:
        print("Setting up...")
        self.setUp()
        print("Testing properties exist...")
        self.test_properties_exist()
        print("Testing methods...")
        self.test_methods()
        print("Testing name...")
        self.test_name()
        print("Testing use x/y/u wire...")
        self.test_use_u_wire()
        self.test_use_x_wire()
        self.test_use_y_wire()
        print("Testing position...")
        self.test_position()
        print("Testing x/y/u size")
        self.test_u_size()
        self.test_x_size()
        self.test_y_size()
        print("Testing inner/outer range...")
        self.test_u_wire_inner()
        self.test_u_wire_outer()
        self.test_x_wire_inner()
        self.test_x_wire_outer()
        self.test_y_wire_inner()
        self.test_y_wire_outer()
        print("Testing initialized...")
        self.test_initialize_status()
        print("Testing homed...")
        self.test_homed()
        print("Testing speed...")
        self.test_speed()
        print("Testing scan pulses...")
        self.test_scan_pulses()
        print("Tests done!")
