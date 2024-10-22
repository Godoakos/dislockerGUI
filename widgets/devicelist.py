import json
import subprocess

import PySide6
from PySide6.QtWidgets import QWidget, QTableWidget, QTableWidgetItem, QVBoxLayout
from PySide6.QtCore import Signal

import os

class QDeviceList(QWidget):
    sig_device_mount = Signal(dict)
    sig_device_unmount = Signal(dict)

    def __init__(self, parent,
                 removeable_only=True,
                 update_interval_ms=2000):
        super().__init__(parent=parent)

        self.parent = parent

        self.removeable_only = removeable_only
        self.header = ["Device", "Size", "Removable", "Bitlocker", "Mounted"]
        self.devices = []

        layout = QVBoxLayout()

        self.table = QTableWidget()
        self.table.setEditTriggers(PySide6.QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setColumnCount(len(self.header))
        self.table.setRowCount(len(self.devices))
        self.table.setHorizontalHeaderLabels(self.header)

        # give the header some margin
        self.table.horizontalHeader().setStyleSheet("QHeaderView::section {padding: 10px;}")
        # and the rows as well
        self.table.setStyleSheet("QTableWidget::item {padding: 10px;}")

        # remove row numbers
        self.table.verticalHeader().setVisible(False)

        # remove focus
        self.table.setFocusPolicy(PySide6.QtCore.Qt.NoFocus)

        self.update_timer = PySide6.QtCore.QTimer()

        self.table.cellDoubleClicked.connect(self.on_dbl_click)
        self.update_timer.timeout.connect(self.update)

        layout.addWidget(self.table)
        self.setLayout(layout)

        self.show()
        self.update_timer.start(update_interval_ms)

    def set_removable_only(self, state: int):
        self.removeable_only = state > 0
        self.update()

    def on_dbl_click(self, row, col):
        if self._is_mounted(row):
            self.sig_device_unmount.emit(self.devices[row])
        else:
            self.sig_device_mount.emit(self.devices[row])

    def _is_mounted(self, device_idx):
        # yeah this has a complexity of O(ass) if you have a lot of devices to check :/
        if self.devices[device_idx]["mountpoints"][0] is not None:
            return True

        # Checking if mounted already as loop device
        dev_id = self.devices[device_idx]["name"].strip().split("/")[-1]
        mountpoint = f"/media/{dev_id}"
        loop_devices = [dev for dev in self._get_devices(device_type="loop",
                                                   name_pattern="loop",
                                                   removables_only=False)]
        for device in loop_devices:
            if device["mountpoints"][0] == mountpoint:
                return True
        return False

    def _is_removable(self, device_idx):
        if self.devices[device_idx]["rm"]:
            return True
        return False

    def _is_dislocker(self, dev_id):
        # check if device is Dislocker
        dislocker_check_cmd = [f"echo {self.parent.sudo_passwd} | sudo -S", "dislocker-find", "2>/dev/null"]
        dislocker_stdout = os.popen(" ".join(dislocker_check_cmd)).read()
        for dislocker_device in dislocker_stdout.split('\n'):
            if dev_id in dislocker_device:
                return True
        return False

    @staticmethod
    def _get_devices(device_type="disk", name_pattern="sd", removables_only=False):
        """
        Returns a sorted list of devices block devices matching the given criteria.
        :param device_type: type of device, e.g. disk, part
        :param name_pattern: pattern to match the device name against e.g. sd for sda, sdb, etc.
        :param removables_only: if True, only removable devices are returned
        :return: sorted list of devices with children unraveled
        """
        lsblk = subprocess.run(["lsblk", "-J"], stdout=subprocess.PIPE)
        raw = lsblk.stdout
        raw = raw.decode("utf-8")
        data = json.loads(raw)
        data = data["blockdevices"]
        data = [device for device in data if device_type in device["type"] and name_pattern in device["name"]]
        if removables_only:
            data = [device for device in data if device["rm"]]
        # unrolling children
        for device in data:
            try:
                while len(device["children"]) > 0:
                    data.append(device["children"].pop(0))
            except KeyError:
                pass
        data = sorted(data, key=lambda x: x["name"])
        return data

    def update(self):
        if not self.isEnabled():
            return
        self.devices = self._get_devices(removables_only=self.removeable_only)
        self.table.clear()
        self.table.setRowCount(0)
        self.table.setHorizontalHeaderLabels(self.header)
        for device in self.devices:
            row = self.table.rowCount()
            self.table.insertRow(row)
            name = QTableWidgetItem(device["name"])
            size = QTableWidgetItem(device["size"])
            removable = QTableWidgetItem("Yes" if self._is_removable(row) else "No")
            mounted = QTableWidgetItem("Yes" if self._is_mounted(row) else "No")
            bitlocker = self._is_dislocker(device["name"])
            self.devices[row]["bitlocker"] = bitlocker
            bitlocker = QTableWidgetItem("Yes" if bitlocker else "No")
            self.table.setItem(row, 0, name)
            self.table.setItem(row, 1, size)
            self.table.setItem(row, 2, removable)
            self.table.setItem(row, 3, bitlocker)
            self.table.setItem(row, 4, mounted)
        self.table.resizeColumnsToContents()
        self.table.resizeRowsToContents()
        self.table.show()
