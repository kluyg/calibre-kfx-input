#!/usr/bin/env python
# vim:fileencoding=UTF-8:ts=4:sw=4:sta:et:sts=4:ai
from __future__ import (unicode_literals, division, absolute_import, print_function)

import argparse
import io
import os
import platform
import sys
import traceback

from calibre.constants import (config_dir, get_version)
from calibre.customize.conversion import (InputFormatPlugin, OptionRecommendation)
from calibre.ebooks import (BOOK_EXTENSIONS, DRMError)
from calibre.ebooks.conversion import ConversionUserFeedBack
from calibre.ebooks.conversion.plugins.epub_input import EPUBInput
from calibre.ebooks.metadata.opf2 import OPF
from calibre.utils.logging import Log


__license__ = "GPL v3"
__copyright__ = "2017-2024, John Howell <jhowell@acm.org>"


class KFXInput(InputFormatPlugin):
    name = "KFX Input"
    author = "jhowell"
    file_types = {"azw8", "kfx", "kfx-zip", "kpf"}
    version = (2, 13, 0)
    minimum_calibre_version = (5, 0, 0)
    supported_platforms = ["windows", "osx", "linux"]
    description = "Convert from Amazon KFX format"

    options = {
        OptionRecommendation(
            name="allow_conversion_with_errors", recommended_value=False,
            help="Allow conversion to proceed even if the KFX book contains unexpected or incorrect data "
            "that may not convert properly. If this option is selected it is recommend that the log of each "
            "conversion be checked for error messages."),
    }

    recommendations = EPUBInput.recommendations

    def __init__(self, *args, **kwargs):
        from calibre_plugins.kfx_input.config import config_allow_import_from_kindles

        self.cli = False
        InputFormatPlugin.__init__(self, *args, **kwargs)

        self.epub_input_plugin = EPUBInput(*args, **kwargs)

        self.resources = self.load_resources(["kfx.png"])

        self.load_kfx_icon()
        self.init_embedded_plugins()

        if config_allow_import_from_kindles():
            self.set_kfx_not_virtual()

        for file_type in self.file_types:
            if file_type not in BOOK_EXTENSIONS:
                BOOK_EXTENSIONS.append(file_type)   # show files of this type in add book format dialog

    def load_kfx_icon(self):
        # calibre does not include an icon for KFX format

        filename = os.path.join(config_dir, "resources", "images", "mimetypes", "kfx.png")
        if not os.path.isfile(filename):
            try:
                os.makedirs(os.path.dirname(filename))
            except Exception:
                pass

            try:
                with open(filename, "wb") as f:
                    f.write(self.resources["kfx.png"])
            except Exception:
                traceback.print_exc()
                print("Failed to create KFX icon file")

    def gui_configuration_widget(self, parent, get_option_by_name, get_option_help, db, book_id=None):
        from calibre_plugins.kfx_input.kfx_input import PluginWidget
        return PluginWidget(parent, get_option_by_name, get_option_help, db, book_id)

    def convert(self, stream, options, file_ext, log, accelerators):
        from calibre_plugins.kfx_input.kfxlib import (clean_message, KFXDRMError, file_write_binary, set_logger, YJ_Book)

        self.report_version(log)

        if (not hasattr(stream, "name")) or (not stream.name.endswith("." + file_ext)):
            self.log.info("Creating temporary file for %s conversion" % file_ext)
            stream.seek(0)
            filename = self.temporary_file("." + file_ext).name
            file_write_binary(filename, stream.read())
            stream = filename

        try:
            job_log = set_logger(JobLog(log))
            job_log.info("Converting %s" % name_of_file(stream))

            book = YJ_Book(stream, symbol_catalog_filename=get_symbol_catalog_filename())
            book.decode_book(retain_yj_locals=True)

            if book.has_pdf_resource:
                job_log.warning(
                    "This book contains PDF content. It can be extracted using either the From KFX user interface "
                    "plugin or the KFX Input plugin CLI. See the KFX Input plugin documentation for more information.")

            if book.is_fixed_layout or book.is_magazine:
                job_log.error(
                    "This book has a layout that is incompatible with calibre conversion. For best results use either "
                    "the From KFX user interface plugin or the KFX Input plugin CLI for conversion. See the KFX Input "
                    "plugin documentation for more information.")

            epub_data = book.convert_to_epub(epub2_desired=getattr(options, "epub_version", "3") == "2")
            set_logger()

            if job_log.errors and not options.allow_conversion_with_errors:
                raise Exception("\n".join(job_log.errors))

        except KFXDRMError:
            raise DRMError('This book has DRM!')

        except Exception as e:
            raise ConversionUserFeedBack(
                    "KFX conversion failed",
                    "<b>Cannot convert %s</b><br><br>%s" % (clean_message(self.get_title(options)), clean_message(repr(e))),
                    level="error")

        log.info("Successfully converted %s to EPUB -- running EPUB input plugin" % file_ext)

        result = self.epub_input_plugin.convert(io.BytesIO(epub_data), options, "epub", log, accelerators)

        log.info("KFX Input plugin processing complete")

        return result

    def get_title(self, options):
        if options.title:
            return options.title

        if options.read_metadata_from_opf:
            try:
                opf_path = os.path.abspath(options.read_metadata_from_opf)
                mi = OPF(open(opf_path, 'rb'), os.path.dirname(opf_path)).to_book_metadata()
                return mi.title
            except Exception:
                pass

        return "?"

    def cli_main(self, argv):
        from calibre_plugins.kfx_input.kfxlib import (file_write_binary, set_logger, YJ_Book)

        self.cli = True
        log = JobLog(Log())
        self.report_version(log)
        log.info("")

        allowed_exts = [".%s" % e for e in sorted(list(self.file_types))]
        ext_choices = ", ".join(allowed_exts[:-1] + ["or " + allowed_exts[-1]])

        parser = argparse.ArgumentParser(
                prog='calibre-debug -r "KFX Input" --',
                description="Convert KFX e-book to EPUB, PDF, CBZ or extract its resources")
        parser.add_argument("infile", help="Pathname of the %s file or notebook folder to be processed" % ext_choices)
        parser.add_argument("outfile", nargs="?", help="Optional pathname of the resulting .epub, .pdf, .cbz, or .zip file")
        parser.add_argument("-e", "--epub", action="store_true", help="Convert to EPUB (default action)")
        parser.add_argument("-2", "--epub2", action="store_true", help="Convert to EPUB 2 instead of EPUB 3")
        parser.add_argument("-p", "--pdf", action="store_true", help="Extract PDF from print replica, create PDF from comics & children's")
        parser.add_argument("-z", "--cbz", action="store_true", help="Create CBZ from print replica, comics, & children's")
        parser.add_argument("-u", "--unpack", action="store_true", help="Create a ZIP file with extracted resources")
        parser.add_argument("-j", "--json-content", action="store_true", help="Create a JSON content/position file")
        parser.add_argument("-c", "--cover", action="store_true", help="Create a generic EPUB cover page if the book does not already have one")
        args = parser.parse_args(argv[1:])

        if os.path.isfile(args.infile):
            intype = os.path.splitext(args.infile)[1]
            if intype not in allowed_exts:
                log.error("Input file must be %s" % ext_choices)
                return
        elif os.path.isdir(args.infile):
            if args.infile.endswith(".sdr"):
                log.error("Input folder must not be SDR: %s" % args.infile)
                return
        else:
            log.error("Input file does not exist: %s" % args.infile)
            return

        log.info("Processing %s" % args.infile)

        set_logger(log)
        book = YJ_Book(args.infile, symbol_catalog_filename=get_symbol_catalog_filename())
        book.decode_book(retain_yj_locals=True)

        if args.unpack:
            zip_data = book.convert_to_zip_unpack()
            output_filename = self.get_output_filename(args, ".zip")
            file_write_binary(output_filename, zip_data)
            log.info("KFX resources unpacked to %s" % output_filename)

        if args.json_content:
            zip_data = book.convert_to_json_content()
            output_filename = self.get_output_filename(args, ".json")
            file_write_binary(output_filename, zip_data)
            log.info("Created JSON content/position file %s" % output_filename)

        if args.cbz:
            if book.is_image_based_fixed_layout:
                cbz_data = book.convert_to_cbz()
                output_filename = self.get_output_filename(args, ".cbz")
                file_write_binary(output_filename, cbz_data)
                log.info("Converted book images to CBZ file %s" % output_filename)
            else:
                log.error("Book format does not support CBZ conversion - must be image based fixed-layout")

        if args.pdf:
            if book.is_image_based_fixed_layout:
                pdf_data = book.convert_to_pdf()
                output_filename = self.get_output_filename(args, ".pdf")
                file_write_binary(output_filename, pdf_data)

                if book.has_pdf_resource:
                    log.info("Extracted PDF content to %s" % output_filename)
                else:
                    log.info("Converted book images to PDF file %s" % output_filename)
            else:
                log.error("Book format does not support PDF conversion - must be image based fixed-layout")
        elif book.has_pdf_resource:
            log.warning("This book contains PDF content. Use the --pdf option to extract it.")

        if args.epub or args.epub2 or not (args.cbz or args.pdf or args.json_content or args.unpack):
            log.info("Converting %s to EPUB" % args.infile)
            epub_data = book.convert_to_epub(epub2_desired=args.epub2, force_cover=args.cover)
            output_filename = self.get_output_filename(args, ".epub")
            file_write_binary(output_filename, epub_data)
            log.info("Converted book saved to %s" % output_filename)

        set_logger()

    def get_output_filename(self, args, extension):
        if args.outfile:
            output_filename = args.outfile
            if output_filename.lower().endswith(extension):
                output_filename = output_filename[:-len(extension)]
        else:
            output_filename = os.path.join(os.path.dirname(args.infile), os.path.splitext(os.path.basename(args.infile))[0])

        return output_filename + extension

    def report_version(self, log):
        try:
            platform_info = platform.platform()
        except Exception:
            platform_info = sys.platform     # handle failure to retrieve platform seen on linux

        log.info("Software versions: %s %s, calibre %s, %s" % (self.name, ".".join([str(v) for v in self.version]),
                 get_version(), platform_info))
        log.info("KFX Input plugin help is available at https://www.mobileread.com/forums/showthread.php?t=291290")

    def init_embedded_plugins(self):
        from calibre.customize.ui import _initialized_plugins
        from calibre_plugins.kfx_input.gather_filetype import GatherKFXZIPFileTypePlugin
        from calibre_plugins.kfx_input.package_filetype import PackageKFXFileTypePlugin
        from calibre_plugins.kfx_input.metadata_reader import KFXMetadataReader
        from calibre_plugins.kfx_input.action_base import ActionFromKFX

        def init_pi(pi_type):
            for plugin in _initialized_plugins:
                if isinstance(plugin, pi_type):
                    return plugin

            pi_type.version = self.version
            plugin = pi_type(self.plugin_path)
            _initialized_plugins.append(plugin)
            plugin.initialize()
            return plugin

        init_pi(GatherKFXZIPFileTypePlugin)
        init_pi(PackageKFXFileTypePlugin)
        init_pi(KFXMetadataReader)
        init_pi(ActionFromKFX)

        #reread_filetype_plugins() and reread_metadata_plugins() will be done in calibre.customize.ui.initialize_plugins()

    def set_kfx_not_virtual(self):
        try:
            from calibre.devices.kindle.driver import KINDLE
            KINDLE.VIRTUAL_BOOK_EXTENSIONS = frozenset(KINDLE.VIRTUAL_BOOK_EXTENSIONS - {"kfx"})
        except Exception:
            print("Failed to set KFX non-virtual")

    def is_customizable(self):
        return True

    def config_widget(self):
        from calibre_plugins.kfx_input.config import ConfigWidget
        return ConfigWidget()

    def save_settings(self, config_widget):
        config_widget.save_settings()


def get_symbol_catalog_filename():
    symbol_catalog_filename = os.path.join(config_dir, "plugins", "kfx_symbol_catalog.ion")
    return symbol_catalog_filename if os.path.isfile(symbol_catalog_filename) else None


def name_of_file(file):
    if isinstance(file, str):
        return file

    if isinstance(file, bytes):
        return repr(file)

    elif hasattr(file, "name"):
        return file.name

    return "unknown"


class JobLog(object):
    '''
    Logger that also collects errors and warnings for presentation in a job summary.
    '''

    def __init__(self, logger):
        self.logger = logger
        self.errors = []
        self.warnings = []

    def debug(self, msg):
        self.logger.debug(msg)

    def info(self, msg):
        self.logger.info(msg)

    def warn(self, msg):
        self.warnings.append(msg)
        self.logger.warn("WARNING: %s" % msg)

    def warning(self, desc):
        self.warn(desc)

    def error(self, msg):
        self.errors.append(msg)
        self.logger.error("ERROR: %s" % msg)

    def exception(self, msg):
        self.errors.append("EXCEPTION: %s" % msg)
        self.logger.exception("EXCEPTION: %s" % msg)

    def __call__(self, *args):
        self.info(" ".join([str(arg) for arg in args]))
