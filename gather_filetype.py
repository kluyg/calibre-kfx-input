from __future__ import (unicode_literals, division, absolute_import, print_function)
import os
import re
import zipfile

from calibre.customize import FileTypePlugin

__license__ = "GPL v3"
__copyright__ = "2017-2024, John Howell <jhowell@acm.org>"


class GatherKFXZIPFileTypePlugin(FileTypePlugin):
    name = "Gather KFX-ZIP (from KFX Input)"
    description = "Import Amazon KFX format Pt 1 - Gather the files that make up a book into KFX-ZIP"
    supported_platforms = ["windows", "osx", "linux"]
    author = "jhowell"
    file_types = {"azw", "azw8", "kfx"}        # file type of main KFX book file
    on_import = True
    priority = 650
    minimum_calibre_version = (5, 0, 0)

    def run(self, path_to_ebook):
        from calibre.utils.logging import Log
        from calibre_plugins.kfx_input.kfxlib import windows_long_path_fix

        log = Log()

        log.info("%s %s: Importing %s" % (self.name, ".".join([str(i) for i in self.version]), path_to_ebook))

        # see if this is a KFX container
        with open(path_to_ebook, "rb") as of:
            data = of.read(16)

        has_kfx_drm = data.startswith(b"\xeaDRMION\xee")
        if not (has_kfx_drm or data.startswith(b"CONT\x02\x00") or data.startswith(b"SQLite format 3\0")):
            log.info("%s: File is not KFX format" % self.name)
            return path_to_ebook

        files = [path_to_ebook]

        # original_path_to_file added in calibre 2.74.0 (Dec 8, 2016)
        orig_path, orig_fn = os.path.split(self.original_path_to_file)
        orig_root, orig_ext = os.path.splitext(orig_fn)
        orig_ext = orig_ext.lower()
        orig_dir = os.path.basename(orig_path)
        sdr_path = os.path.join(orig_path, orig_root + ".sdr")

        #log.info("orig_path: %s" % orig_path)
        #log.info("orig_fn: %s" % orig_fn)
        #log.info("orig_root: %s" % orig_root)
        #log.info("orig_ext: %s" % orig_ext)
        #log.info("orig_dir: %s" % orig_dir)
        #log.info("sdr_path: %s" % sdr_path)

        if orig_ext == ".kfx" and os.path.isdir(sdr_path):
            # e-ink Kindle
            for dirpath, dns, fns in os.walk(sdr_path):
                for fn in fns:
                    if (fn.lower().endswith(".kfx") and fn != orig_fn) or fn.lower() == "voucher":
                        files.append(os.path.join(dirpath, fn))

        elif orig_ext == ".azw" and re.match("^B[A-Z0-9]{9}_(EBOK|EBSP)$", orig_dir):
            # Kindle for PC and Kindle for Mac Classic
            for dirpath, dns, fns in os.walk(orig_path):
                for fn in fns:
                    if (os.path.splitext(fn)[1].lower() in [".md", ".res", ".voucher"] and
                            not fn.startswith("._")):
                        files.append(os.path.join(dirpath, fn))

        elif orig_ext == ".kfx" and re.match("^B[A-Z0-9]{9}(_sample)?$", orig_dir):
            # Kindle for Android and Fire
            for dirpath, dns, fns in os.walk(orig_path):
                for fn in fns:
                    if os.path.splitext(fn)[1].lower() in [".ast", ".kfx"] and fn != orig_fn:
                        files.append(os.path.join(dirpath, fn))

        elif (orig_ext == ".azw8" or orig_fn == "BookManifest.kfx") and re.match("^[0-9a-f-]{36}$", orig_dir, flags=re.IGNORECASE):
            # Kindle for iOS and Mac (for possible future use, untested)
            if orig_fn == "BookManifest.kfx":
                files.pop(0)    # discard SQLite file with book bundle info

            for dirpath, dns, fns in os.walk(orig_path):
                for fn in fns:
                    if (os.path.splitext(fn)[1].lower() in [".azw8", ".azw9", ".md", ".res", ".voucher"] and
                            fn != orig_fn and not fn.startswith("._")):
                        files.append(os.path.join(dirpath, fn))

        elif has_kfx_drm:
            log.info((
                "%s: Cannot locate some files needed for the book. KFX files must remain in their original "
                "folder structure for successful import. ") % self.name)

        if len(files) == 1 and not has_kfx_drm:
            log.info("%s: Single KFX file found." % self.name)
            return path_to_ebook

        zfile = self.temporary_file(".kfx-zip")

        with zipfile.ZipFile(zfile, "w", compression=zipfile.ZIP_STORED) as zf:
            for filepath in files:
                zf.write(windows_long_path_fix(filepath), os.path.basename(filepath))

        log.info("%s: Gathered %d file(s) as %s" % (self.name, len(files), zfile.name))
        return zfile.name

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.kfx_input.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()
