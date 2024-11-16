from __future__ import (unicode_literals, division, absolute_import, print_function)

from PyQt5.Qt import (QGroupBox, QVBoxLayout, QWidget, QCheckBox)

from calibre.utils.config import JSONConfig
from calibre.utils.config_base import tweaks


__license__ = "GPL v3"
__copyright__ = "2017-2024, John Howell <jhowell@acm.org>"

# Individual Setting names
AllowImportFromKindles = "AllowImportFromKindles"
SplitLandscapeComicImages = "SplitLandscapeComicImages"

# Set location where all preferences for this plugin will be stored
plugin_config = JSONConfig("plugins/KFX Input")

# Default values
plugin_config.defaults[AllowImportFromKindles] = not tweaks.get("kfx_input_set_format_virtual", True)   # value used previously
plugin_config.defaults[SplitLandscapeComicImages] = False


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

        self.SplitLandscapeComicImages = QCheckBox("Split landscape images when converting comics to CBZ or PDF")
        self.SplitLandscapeComicImages.setToolTip(
            "Causes landscape orientation images in comics to be split into separate left and right side images "
            "when converting to CBZ or PDF format. This is intended to break page spreads into individual page "
            "images. This option only applies to conversion done using the plugin CLI or From KFX GUI, not "
            "conversion using calibre's Convert Books feature.")
        layout.addWidget(self.SplitLandscapeComicImages)
        self.SplitLandscapeComicImages.setChecked(plugin_config[SplitLandscapeComicImages])

        layout.addStretch()
        return group_box

    def save_settings(self):
        # Called by calibre when the configuration dialog has been accepted
        plugin_config[AllowImportFromKindles] = self.AllowImportFromKindles.isChecked()
        plugin_config[SplitLandscapeComicImages] = self.SplitLandscapeComicImages.isChecked()


def config_allow_import_from_kindles():
    return plugin_config[AllowImportFromKindles]


def config_split_landscape_comic_images():
    return plugin_config[SplitLandscapeComicImages]
