#! /usr/bin/python3

from __future__ import (unicode_literals, division, absolute_import, print_function)

from calibre.customize import InterfaceActionBase


__license__ = "GPL v3"
__copyright__ = "2017-2024, John Howell <jhowell@acm.org>"


class ActionFromKFX(InterfaceActionBase):
    name = "From KFX"
    description = "Convert books from KFX format without using the calibre conversion pipeline"
    supported_platforms = ["windows", "osx", "linux"]
    author = "jhowell"
    minimum_calibre_version = (5, 0, 0)
    actual_plugin = "calibre_plugins.kfx_input.action:FromKFXAction"

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.kfx_input.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
