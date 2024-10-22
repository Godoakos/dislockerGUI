import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QCheckBox, QHBoxLayout, QComboBox, QLabel

from widgets.devicelist import QDeviceList
from dialogs.pwdialog import QSudoPasswordDialog, QDislockerPasswordDialog
from dialogs.msgdialog import QMessageDialog

class DislockerGUI(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setStyleSheet("font-size: 24px;")

        self.setWindowTitle("Dislocker GUI")
        self.setGeometry(100, 100, 800, 600)
        layout_main = QVBoxLayout()
        layout_ctls = QHBoxLayout()

        self.device_table = QDeviceList(parent=self,
                                        removeable_only=True)
        self.device_table.setEnabled(False)
        self.device_table.sig_device_mount.connect(self.mount_device)
        self.device_table.sig_device_unmount.connect(self.unmount_device)

        self.checkbox_removables = QCheckBox("Removables only")
        self.checkbox_removables.setCheckState(Qt.CheckState.Checked)
        self.checkbox_removables.stateChanged.connect(self.device_table.set_removable_only)

        label_filesystems = QLabel("Filesystem:")
        label_filesystems.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.dropdown_filesystems = QComboBox()
        self.dropdown_filesystems.addItems(["exfat", "ntfs"])
        # TODO: is there a way to know what FS the device is formatted with before mounting it?

        layout_ctls.addWidget(self.checkbox_removables)
        layout_ctls.addWidget(label_filesystems)
        layout_ctls.addWidget(self.dropdown_filesystems)

        layout_main.addWidget(self.device_table)
        layout_main.addLayout(layout_ctls)
        widget = QWidget()
        widget.setLayout(layout_main)
        self.setCentralWidget(widget)

        self.setEnabled(False)
        self.show()

        self.sudo_passwd = QSudoPasswordDialog(self)
        if self.sudo_passwd.exec() == QSudoPasswordDialog.Accepted:
            self.sudo_passwd = self.sudo_passwd.input.text()
        else:
            self.close()
        self.device_table.setEnabled(True)
        self.setEnabled(True)
        self.device_table.update()

    def is_dislocker_mountpt(self, keyfile_mountpoint):
        """
        Check if the provided mountpoint is a dislocker mountpoint.
        :param keyfile_mountpoint:
        :return:
        """
        if os.path.exists(keyfile_mountpoint + "/dislocker-file"):
            return True

        dislocker_mountpoint_check_cmd = [f"echo {self.sudo_passwd} | sudo -S", "findmnt", "--mountpoint",
                                          keyfile_mountpoint]
        dislocker_check = os.popen(" ".join(dislocker_mountpoint_check_cmd))
        dislocker_check = dislocker_check.read()
        if "fuse.dis" in dislocker_check:
            return True

        return False

    def is_device_mountpt(self, mountpt):
        mountpt_check_cmd = [f"echo {self.sudo_passwd} | sudo -S", "findmnt",
                             "--mountpoint", mountpt]
        mountpt_check = os.popen(" ".join(mountpt_check_cmd)).read()
        if len(mountpt_check) > 0:
            return True
        return False

    def is_dislocker(self, device):
        return device["bitlocker"]

    def mount_device(self, device):
        dev_id = device["name"].strip().split("/")[-1]
        keyfile_mountpoint = f"/media/{dev_id}_dislocker"
        mountpoint = f"/media/{dev_id}"
        fs = self.dropdown_filesystems.currentText()

        # check if device is Dislocker
        if not self.is_dislocker(device):
            QMessageDialog(self, "Not a BitLocker device",
                           f"/dev/{dev_id} is not a BitLocker device, please mount it manually",
                           icon=QMessageDialog.Warning)
            return 1

        # check if keyfile is mounted
        if not self.is_dislocker_mountpt(keyfile_mountpoint):
            if self._mount_keyfile(device): # mount the keyfile
                QMessageDialog(self, "Mount Keyfile failed",
                               f"Failed to mount /dev/{dev_id} keyfile to /media/{dev_id}_dislocker",
                               icon=QMessageDialog.Warning)
                return 1

        # check if loop device is mounted
        if not self.is_device_mountpt(mountpoint):
            if self._mount_loop_device(device):
                self._unmount_keyfile(device)
                QMessageDialog(self, "Mount failed",
                               f"Failed to mount /dev/{dev_id} to /media/{dev_id} as {fs}",
                               icon=QMessageDialog.Warning)
                return 1

        QMessageDialog(self, "Device mounted",
                       f"/dev/{dev_id} mounted successfully to /media/{dev_id} as {fs}",
                       icon=QMessageDialog.Information)
        return 0

    def unmount_device(self, device):
        dev_id = device["name"].strip().split("/")[-1]

        if not self.is_dislocker(device):
            QMessageDialog(self, "Not a BitLocker device",
                           f"/dev/{dev_id} is not a BitLocker device, please unmount it manually",
                           icon=QMessageDialog.Warning)
            return 1

        if not self.is_device_mountpt(f"/media/{dev_id}"):
            QMessageDialog(self, "Device not managed",
                           f"/dev/{dev_id} is not mounted to /media/{dev_id}, unmount it manually",
                           icon=QMessageDialog.Warning)
            return 1

        if self._unmount_loop_device(device):
            QMessageDialog(self, "Unmount Loop Device failed",
                           f"Failed to unmount /dev/{dev_id} from /media/{dev_id}",
                           icon=QMessageDialog.Warning)
            return 1
        if self._unmount_keyfile(device):
            QMessageDialog(self, "Unmount Keyfile failed",
                           f"Failed to unmount /dev/{dev_id} keyfile from /media/{dev_id}_dislocker",
                           icon=QMessageDialog.Warning)
            return 1

        QMessageDialog(self, "Device unmounted",
                       f"/dev/{dev_id} unmounted successfully",
                       icon=QMessageDialog.Information)
        return 0

    def _mount_keyfile(self, device):
        dev_id = device["name"].strip().split("/")[-1]
        keyfile_mountpoint = f"/media/{dev_id}_dislocker"

        # mount the keyfile
        if not os.path.exists(keyfile_mountpoint):  # create the mountpoint if it doesn't exist
            os.system(f"echo {self.sudo_passwd} | sudo -S mkdir {keyfile_mountpoint}")

        success = False
        while not success:
            dislocker_passwd = QDislockerPasswordDialog(self)  # get the BitLocker user password
            if dislocker_passwd.exec() == QDislockerPasswordDialog.Accepted:
                dislocker_passwd = dislocker_passwd.input.text()
            else:
                return 1

            # mount the keyfile
            dislocker_cmd = [f"echo {self.sudo_passwd} | sudo -S", "dislocker", f"-u{dislocker_passwd}",
                             f"-V /dev/{device['name']}", keyfile_mountpoint]
            dislocker = os.system(" ".join(dislocker_cmd))
            success = dislocker == 0
        return 0

    def _mount_loop_device(self, device):
        device_id = device["name"].strip().split("/")[-1]
        mountpoint = f"/media/{device_id}"
        keyfile_mountpoint = f"/media/{device_id}_dislocker"
        fs = self.dropdown_filesystems.currentText()

        mount_cmd = [f"echo {self.sudo_passwd} | sudo -S", "mount", "-o", f"uid={os.getuid()},gid={os.getgid()},rw",
                     "-t", fs,
                     keyfile_mountpoint + "/dislocker-file",
                     mountpoint, ]

        if not os.path.exists(mountpoint):
            os.system(
                f"echo {self.sudo_passwd} | sudo -S mkdir {mountpoint}")  # create the mountpoint if it doesn't exist
        # make mountpoint owned by the user
        os.system(f"echo {self.sudo_passwd} | sudo -S chown $USER:$USER {mountpoint}")

        # return the return code of mount command
        return os.system(" ".join(mount_cmd))

    def _unmount_loop_device(self, device):
        dev_id = device["name"].strip().split("/")[-1]
        unmount_cmd = [f"echo {self.sudo_passwd} | sudo -S", "umount", f"/media/{dev_id}"]
        rmdir_cmd = [f"echo {self.sudo_passwd} | sudo -S", "rm -rf", f"/media/{dev_id}"]
        if os.system(" ".join(unmount_cmd)) == 0:
            os.system(" ".join(rmdir_cmd))
            return 0
        return 1

    def _unmount_keyfile(self, device):
        dev_id = device["name"].strip().split("/")[-1]
        unmount_cmd = [f"echo {self.sudo_passwd} | sudo -S", "umount", f"/media/{dev_id}_dislocker"]
        rmdir_cmd = [f"echo {self.sudo_passwd} | sudo -S", "rm -rf", f"/media/{dev_id}_dislocker"]
        if os.system(" ".join(unmount_cmd)) == 0:
            os.system(" ".join(rmdir_cmd))
            return 0
        return 1


if __name__ == "__main__":
    app = QApplication([])
    window = DislockerGUI()
    window.show()
    app.exec()
