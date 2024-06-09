#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

from PyQt5 import (QtCore, QtWidgets)
from calibre.gui2.convert import Widget


__license__ = "GPL v3"
__copyright__ = "2017-2024, John Howell <jhowell@acm.org>"

# the file name kfx_input and class name PluginWidget are required for calibre to access this properly
# see config_widget_for_input_plugin() in gui2/convert/__init__.py


class PluginWidget(Widget):
    TITLE = "KFX Input"
    HELP = "Options specific to KFX input"
    ICON = I("mimetypes/kfx.png")
    COMMIT_NAME = "kfx_input"           # where option values are saved

    def __init__(self, parent, get_option, get_help, db=None, book_id=None):
        self.db = db                # db is set for conversion, but not default preferences
        self.book_id = book_id      # book_id is set for individual conversion, but not bulk

        Widget.__init__(self, parent, ["allow_conversion_with_errors"])
        self.initialize_options(get_option, get_help, db, book_id)

    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.setWindowTitle("Form")
        Form.resize(588, 481)

        self.formLayout = QtWidgets.QFormLayout(Form)
        self.formLayout.setObjectName("formLayout")

        self.opt_allow_conversion_with_errors = QtWidgets.QCheckBox(Form)
        self.opt_allow_conversion_with_errors.setObjectName("opt_allow_conversion_with_errors")
        self.opt_allow_conversion_with_errors.setText("Allow conversion to complete even if errors are detected")
        self.formLayout.addRow(self.opt_allow_conversion_with_errors)

        self.formLayout.addItem(QtWidgets.QSpacerItem(20, 40, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding))

        self.help_label = QtWidgets.QLabel(Form)
        self.help_label.setWordWrap(True)
        self.help_label.setOpenExternalLinks(True)
        self.help_label.setObjectName("help_label")
        self.help_label.setText(
            '<p>KFX Input plugin help is available at '
            '<a href="http://www.mobileread.com/forums/showthread.php?t=291290">'
            'http://www.mobileread.com/forums/showthread.php?t=291290</a>.</p>')
        self.formLayout.addRow(self.help_label)

        QtCore.QMetaObject.connectSlotsByName(Form)
