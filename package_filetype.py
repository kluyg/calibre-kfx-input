from __future__ import (unicode_literals, division, absolute_import, print_function)

import os

from calibre.customize import FileTypePlugin

__license__ = "GPL v3"
__copyright__ = "2017-2024, John Howell <jhowell@acm.org>"


class PackageKFXFileTypePlugin(FileTypePlugin):
    name = "Package KFX (from KFX Input)"
    description = "Import Amazon KFX format Pt 2 - package a KFX-ZIP book into monolithic KFX"
    supported_platforms = ["windows", "osx", "linux"]
    author = "jhowell"
    file_types = {"azw", "azw8", "kfx", "kfx-zip", "zip"}     # original type - any type that could turn into kfx-zip
    on_import = True
    priority = 200
    minimum_calibre_version = (5, 0, 0)

    def run(self, path_to_ebook):
        if os.path.splitext(path_to_ebook)[1].lower() == ".kfx-zip":
            return self.package_kfx(path_to_ebook)

        return path_to_ebook

    def package_kfx(self, path_to_ebook):
        from calibre.utils.logging import Log
        from calibre_plugins.kfx_input.kfxlib import (file_write_binary, set_logger, YJ_Book)

        log = set_logger(Log())
        log.info("%s %s: Packaging %s" % (self.name, ".".join([str(i) for i in self.version]), path_to_ebook))

        kfx_data = YJ_Book(path_to_ebook).convert_to_single_kfx()
        set_logger()

        outfile = self.temporary_file(".kfx").name
        file_write_binary(outfile, kfx_data)

        log.info("%s: Imported as KFX" % self.name)
        return outfile

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.kfx_input.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
