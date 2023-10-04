from functools import partial

from PyQt5.QtCore import QObject, pyqtSignal
from PyQt5.QtWidgets import QLabel, QMessageBox, QWidget
from qtpy.QtCore import Slot

ERROR_STYLESHEET = "color: rgb(128, 0, 2);"
FINISHED_STYLESHEET = "color: rgb(16, 128, 1);"
STATUS_STYLESHEET = "color: rgb(7, 64, 128);"


class WorkerSignals(QObject):
    status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    abort = pyqtSignal(bool)

    def __init__(self, label: QLabel = None):
        super().__init__()
        if label:
            self.status.connect(label.setText)
            self.status.connect(partial(label.setStyleSheet, STATUS_STYLESHEET))

            self.finished.connect(label.setText)
            self.finished.connect(partial(label.setStyleSheet, FINISHED_STYLESHEET))

            self.error.connect(label.setText)
            self.error.connect(partial(label.setStyleSheet, ERROR_STYLESHEET))

            self.abort.connect(label.setText)
            self.abort.connect(partial(label.setStyleSheet, ERROR_STYLESHEET))

        self.status.connect(print)
        self.finished.connect(print)
        self.error.connect(print)
        self.abort.connect(print)


# Making this a Qt slot for connecting to Qt signals (i.e. buttons that open screens)
@Slot()
def showDisplay(display: QWidget):
    display.show()

    # brings the display to the front
    display.raise_()

    # gives the display focus
    display.activateWindow()


def make_error_popup(title, expert_edmbutton, exception, action_func):
    popup = QMessageBox()
    popup.setIcon(QMessageBox.Critical)
    popup.setWindowTitle(title)
    popup.setText(
        "{error}\nPlease check expert screen and select from the options below".format(
            error=exception
        )
    )
    popup.addButton("Abort", QMessageBox.RejectRole)
    popup.addButton(
        "Acknowledge manual completion and continue", QMessageBox.AcceptRole
    )
    popup.addButton(expert_edmbutton, QMessageBox.ActionRole)
    if action_func:
        popup.buttonClicked.connect(partial(action_func, popup))
    popup.exec()


def make_info_popup(text):
    popup = QMessageBox()
    popup.setIcon(QMessageBox.Information)
    popup.setText(text)
    popup.exec()
    return popup
