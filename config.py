from __future__ import (unicode_literals, division, absolute_import, print_function)

from PyQt5.Qt import (QGroupBox, QVBoxLayout, QWidget, QCheckBox)

from calibre.utils.config import JSONConfig
from calibre.utils.config_base import tweaks


__license__ = "GPL v3"
__copyright__ = "2017-2024, John Howell <jhowell@acm.org>"

# Individual Setting names
AllowImportFromKindles = "AllowImportFromKindles"

# Set location where all preferences for this plugin will be stored
plugin_config = JSONConfig("plugins/KFX Input")

# Default values
plugin_config.defaults[AllowImportFromKindles] = not tweaks.get("kfx_input_set_format_virtual", True)   # value used previously


class ConfigWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        layout = QVBoxLayout(self)
        layout.addWidget(self.options_group_box())
        layout.addStretch()
        self.setLayout(layout)

    def options_group_box(self):
        group_box = QGroupBox("Options:", self)
        layout = QVBoxLayout()
        group_box.setLayout(layout)

        self.AllowImportFromKindles = QCheckBox("Allow import of KFX format books from Kindles")
        self.AllowImportFromKindles.setToolTip(
            "KFX is normally blocked from import by calibre since it cannot be handled unless this plugin\n"
            "is installed. A restart is required if this setting is changed.")
        layout.addWidget(self.AllowImportFromKindles)
        self.AllowImportFromKindles.setChecked(plugin_config[AllowImportFromKindles])

        layout.addStretch()
        return group_box

    def save_settings(self):
        # Called by calibre when the configuration dialog has been accepted
        plugin_config[AllowImportFromKindles] = self.AllowImportFromKindles.isChecked()


def config_allow_import_from_kindles():
    return plugin_config[AllowImportFromKindles]
