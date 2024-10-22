from PySide6.QtWidgets import QMessageBox


class QMessageDialog(QMessageBox):
    def __init__(self, parent, title, message, icon=QMessageBox.Information):
        super(QMessageDialog, self).__init__(parent)
        self.setIcon(icon)
        self.setWindowTitle(title)
        self.setText(message)
        self.setStandardButtons(QMessageBox.Ok)
        self.exec_()
