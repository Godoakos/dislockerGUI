"""
Dialogs for the password input.
Hides the input with asterisks.
"""

from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton
from PySide6.QtWidgets import QApplication

import os

class QPasswordDialog(QDialog):
    def __init__(self, parent, title="Enter password:"):
        super().__init__(parent=parent)

        self.setStyleSheet("font-size: 24px;")

        self.setWindowTitle(title)

        layout = QVBoxLayout()
        self.label = QLabel("Enter password:")
        layout.addWidget(self.label)
        self.input = QLineEdit()
        self.input.setEchoMode(QLineEdit.EchoMode.Password)
        layout.addWidget(self.input)
        self.button = QPushButton("OK")
        layout.addWidget(self.button)
        self.setLayout(layout)
        self.button.clicked.connect(self.test_password)

    def test_password(self,):
        return self.accept()


class QSudoPasswordDialog(QPasswordDialog):
    def __init__(self, parent, title="Enter sudo password"):
        super().__init__(parent, title)

    def test_password(self):
        """
        Test if the sudo password is correct.
        :return:
        """
        self.input.setDisabled(True)
        sudo = os.system(f"echo {self.input.text()} | sudo -S ls / >> /dev/null 2>&1")
        correct = sudo == 0
        if correct:
            self.accept()
        else:
            self.input.clear()
            self.label.setText("Password incorrect")
            self.input.setDisabled(False)


class QDislockerPasswordDialog(QPasswordDialog):
    def __init__(self, parent, title="Enter BitLocker password"):
        super().__init__(parent, title)


if __name__ == '__main__':
    app = QApplication([])
    dialog = QSudoPasswordDialog()
    dialog.exec()
    print(dialog.result())
    print(dialog.input.text())
