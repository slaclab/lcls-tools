from pydm import Display

from lcls_tools.superconducting.scLinac.scLinac import Magnet


class MagnetScreen(Display):
    def __init__(self, parent=None, args=None):
        super().__init__(parent, args)

    def ui_filename(self):
        return 'magnet_template.ui'

    def connectSignals(self, magnet: Magnet):
        self.ui.

    def update_magnets(self):
        for magnettype, edmbutton in self._magnet_edm_buttons.items():
            edmbutton.macros = ["DEV={dev}".format(dev=self.current_cm.magnet_name_map[magnettype].pvprefix[:-1])]
        self.magnet_checkout_window.ui.magnet_groupbox.setTitle('CM{cm}'.format(cm=self.current_cm.name))
        for magnetprefix in ['Quad', 'XCor', 'YCor']:
            magnet_object = self.current_cm.magnet_name_map[magnetprefix]
            self.magnet_interlock_indicators[magnetprefix].channel = magnet_object.interlockPV.pvname
            self.magnet_interlock_labels[magnetprefix].channel = magnet_object.interlockPV.pvname
            self.magnet_ps_status_labels[magnetprefix].channel = magnet_object.ps_statusPV.pvname
            self.magnet_ps_status_indicators[magnetprefix].channel = magnet_object.ps_statusPV.pvname

    def get_magnet_labels(self):
        magnet_VBoxLayout_list: List[
            QVBoxLayout] = self.magnet_checkout_window.ui.magnet_template_repeater.findChildren(QVBoxLayout)
        for VBoxLayout in magnet_VBoxLayout_list:
            # the interlock status is the first element in the ui-file, with the byte indicator in 2nd and the text
            # label in 3rd position, hence '0' then '1' and '2'
            interlock_indicator: PyDMByteIndicator = VBoxLayout.itemAt(0).itemAt(1).widget()
            interlock_label: PyDMLabel = VBoxLayout.itemAt(0).itemAt(2).widget()
            self.magnet_interlock_labels[interlock_label.accessibleName()] = interlock_label
            self.magnet_interlock_indicators[interlock_indicator.accessibleName()] = interlock_indicator

            # the magnet reset button is the second item in the ui-file, hence '1'
            reset_button: QPushButton = VBoxLayout.itemAt(1).widget()
            reset_button.clicked.connect(partial(self.magnet_control, reset_button.accessibleName(),
                                                 util.MAGNET_RESET_VALUE))

            # the power supply status is the third element in the ui-file, with the byte indicator in 2nd and the
            # text label in 3rd position, hence '2' then '1' and '2'
            ps_status_indicator: PyDMByteIndicator = VBoxLayout.itemAt(2).itemAt(1).widget()
            ps_status_label: PyDMLabel = VBoxLayout.itemAt(2).itemAt(2).widget()
            self.magnet_ps_status_labels[ps_status_label.accessibleName()] = ps_status_label
            self.magnet_ps_status_indicators[ps_status_indicator.accessibleName()] = ps_status_indicator

            # the power supply on button is the 1st item in a horizontal layout in 4th place in the ui-file,
            # hence '3' and then '0'
            on_button: QPushButton = VBoxLayout.itemAt(3).itemAt(0).widget()
            on_button.clicked.connect(partial(self.magnet_control, on_button.accessibleName(), util.MAGNET_ON_VALUE))

            # the power supply off button is the 2nd item in a horizontal layout in 4th place in the ui-file,
            # hence '3' and then '1'
            off_button: QPushButton = VBoxLayout.itemAt(3).itemAt(1).widget()
            off_button.clicked.connect(partial(self.magnet_control, off_button.accessibleName(), util.MAGNET_OFF_VALUE))

            # the degauss button is the 5th item in the ui-file, hence '4'
            degauss_button: QPushButton = VBoxLayout.itemAt(4).widget()
            degauss_button.clicked.connect(
                    partial(self.magnet_control, degauss_button.accessibleName(), util.MAGNET_DEGAUSS_VALUE))

            # the nominal trim button is the 6th element in the ui-file, hence '5'
            nominal_trim_button: QPushButton = VBoxLayout.itemAt(5).widget()
            nominal_trim_button.setText('Set BDES to {nominalbdes} and trim'.format(nominalbdes=util.NOMINAL_BDES))
            nominal_trim_button.clicked.connect(
                    partial(self.magnet_trim, nominal_trim_button.accessibleName(), util.NOMINAL_BDES))

            # the zero trim button is the 7th element in the ui-file, hence '6'
            zero_trim_button: QPushButton = VBoxLayout.itemAt(6).widget()
            zero_trim_button.clicked.connect(
                    partial(self.magnet_trim, zero_trim_button.accessibleName(), 0))

            # the edm expert display button is the 9th element in the ui-file, hence '8'
            magnet_expert_button: PyDMEDMDisplayButton = VBoxLayout.itemAt(8).widget()
            self._magnet_edm_buttons[magnet_expert_button.accessibleName()] = magnet_expert_button

    def magnet_control(self, accessible_name, enum_value):
        self.current_cm.magnet_name_map[accessible_name].controlPV.put(enum_value)

    def magnet_trim(self, accessible_name, bdes):
        self.current_cm.magnet_name_map[accessible_name].bdesPV.put(bdes)
        self.magnet_control(accessible_name, util.MAGNET_TRIM_VALUE)
