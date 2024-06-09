from __future__ import (unicode_literals, division, absolute_import, print_function)

from functools import partial
import html
import os
import platform
import re
import sys
import time
import traceback

from PyQt5.Qt import (Qt, QApplication, QDialog, QIcon, QLabel, QMenu, QToolButton, QVBoxLayout)

from calibre.constants import (get_version, numeric_version)
from calibre.gui2 import (error_dialog, info_dialog, open_url, question_dialog)
from calibre.gui2.actions import InterfaceAction
from calibre.ptempfile import PersistentTemporaryFile
from calibre.utils.logging import (ANSIStream, GUILog)

from calibre_plugins.kfx_input import (get_symbol_catalog_filename, KFXInput)
from calibre_plugins.kfx_input.action_base import (ActionFromKFX, get_icons)
from calibre_plugins.kfx_input.kfxlib import (file_write_binary, KFXDRMError, set_logger, YJ_Book)


__license__ = "GPL v3"
__copyright__ = "2017-2024, John Howell <jhowell@acm.org>"

# resources contained in the plugin zip file
PLUGIN_ICON = "from_kfx_icon.png"


class FromKFXAction(InterfaceAction):
    name = ActionFromKFX.name
    type = ActionFromKFX.type
    version = KFXInput.version

    # Create our top-level menu/toolbar action (text, icon_path, tooltip, keyboard shortcut)
    action_spec = (ActionFromKFX.name, None, ActionFromKFX.description, None)
    popup_type = QToolButton.InstantPopup
    dont_add_to = frozenset(["menubar-device", "context-menu-device"])
    action_type = "current"

    def genesis(self):
        self.status_cache = {}
        self.icon = get_icons(PLUGIN_ICON, self.name) if numeric_version >= (5, 99, 3) else get_icons(PLUGIN_ICON)
        self.qaction.setIcon(self.icon)

        self.create_menu_actions()
        self.gui.keyboard.finalize()

        self.menu = QMenu(self.gui)
        self.set_default_menu()
        self.menu.aboutToShow.connect(self.set_customized_menu)
        self.menu.aboutToHide.connect(self.set_default_menu)
        self.qaction.setMenu(self.menu)

    def create_menu_actions(self):
        self.default_menu = m = QMenu(self.gui)

        # Actions that operate on the current selection

        self.convert_book_to_epub_action = self.create_menu_action(
            m, "FromKFXConvertBooksEPUB",
            "Convert selected book to EPUB", "convert.png",
            description="Convert selected book from KFX format to EPUB",
            triggered=partial(self.perform_conversion, "epub"))

        self.convert_book_to_pdf_action = self.create_menu_action(
            m, "FromKFXConvertBooksPDF",
            "Convert selected book to PDF", "convert.png",
            description="Convert selected book from KFX format to PDF",
            triggered=partial(self.perform_conversion, "pdf"))

        self.convert_book_to_cbz_action = self.create_menu_action(
            m, "FromKFXConvertBooksCBZ",
            "Convert selected book to CBZ", "convert.png",
            description="Convert selected book from KFX format to CBZ",
            triggered=partial(self.perform_conversion, "cbz"))

        m.addSeparator()

        # Actions that are not selection-based

        self.customize_action = self.create_menu_action(
            m, "FromKFXCustomize", "Customize plugin", "config.png",
            description="Configure the settings for this plugin",
            triggered=self.show_configuration)

        self.help_action = self.create_menu_action(
            m, "FromKFXHelp", "Help", "help.png",
            description="Display help for this plugin",
            triggered=self.show_help)

        # temporary actions and error messages (Not default actions)

        self.temp_menu = QMenu(self.gui)
        m = self.temp_menu

        self.input_format_error_action = self.add_menu_action(
            m, "(Selected book has no KFX format)", "dialog_error.png",
            "Book does not contain KFX, KFX-ZIP, or KPF format - Import a book in KFX format to be converted", enabled=False)

        self.drm_error_action = self.add_menu_action(
            m, "(Selected book has DRM)", "dialog_error.png",
            "Book is locked with DRM and cannot be converted", enabled=False)

        self.select_none_error_action = self.add_menu_action(
            m, "(No selected book)", "dialog_error.png",
            "No book is selected - Select a single book with KFX format for conversion", enabled=False)

        self.select_multiple_error_action = self.add_menu_action(
            m, "(Multiple selected books)", "dialog_error.png",
            "Multiple books are selected - Select a single book with KFX format for conversion", enabled=False)

        self.format_actions = {
            #"kfx": self.add_menu_action(m, "(Found KFX format)", "dialog_error.png", "", enabled=False),
            "kfx-zip": self.add_menu_action(m, "(Found KFX-ZIP format)", "dialog_error.png", "", enabled=False),
            "kpf": self.add_menu_action(m, "(Found KPF format)", "dialog_error.png", "", enabled=False)
            }

    def set_default_menu(self):
        # Copy actions from the default menu to the current menu
        self.menu.clear()

        for a in QMenu.actions(self.default_menu):
            self.menu.addAction(a)

    def set_customized_menu(self):
        # Build menu on the fly based on the number of books selected and actual formats
        m = self.menu
        m.clear()

        if self.gui.library_view.selectionModel().hasSelection():
            if len(self.gui.library_view.selectionModel().selectedRows()) == 1:
                # If single book selected then check for KFX format
                book_id = self.gui.library_view.get_selected_ids()[0]
                input_format = self.kfx_format(book_id)

                if input_format:
                    db = self.gui.current_db.new_api
                    file_name = db.format_abspath(book_id, input_format)    # original file used only for date check
                    modified_dt = os.path.getmtime(file_name) if os.path.isfile(file_name) else None

                    if file_name in self.status_cache and self.status_cache[file_name][0] == modified_dt:
                        is_drm_free, is_image_based = self.status_cache[file_name][1]
                    else:
                        try:
                            input_file_name = db.format(book_id, input_format, as_file=False, as_path=True, preserve_filename=True)
                            set_logger()
                            book = YJ_Book(input_file_name)
                            book.decode_book(retain_yj_locals=True)
                        except KFXDRMError:
                            is_drm_free = is_image_based = False
                        except Exception:
                            traceback.print_exc()
                            is_drm_free = True
                            is_image_based = False
                        else:
                            is_drm_free = True
                            is_image_based = book.is_image_based_fixed_layout

                        self.status_cache[file_name] = (modified_dt, (is_drm_free, is_image_based))     # cache for fast access

                    if input_format in self.format_actions:
                        m.addAction(self.format_actions[input_format])

                    if is_drm_free:
                        m.addAction(self.convert_book_to_epub_action)

                        if is_image_based:
                            m.addAction(self.convert_book_to_pdf_action)
                            m.addAction(self.convert_book_to_cbz_action)
                    else:
                        m.addAction(self.drm_error_action)
                else:
                    m.addAction(self.input_format_error_action)
            else:
                m.addAction(self.select_multiple_error_action)
        else:
            m.addAction(self.select_none_error_action)

        m.addSeparator()

        m.addAction(self.customize_action)
        m.addAction(self.help_action)

    def book_formats(self, book_id):
        return set([x.lower().strip() for x in self.gui.current_db.new_api.formats(book_id)])

    def kfx_format(self, book_id):
        formats = self.book_formats(book_id)
        for input_format in ["kfx", "kfx-zip", "kpf"]:
            # choose highest priority format that this book has (if any)
            if input_format in formats:
                return input_format
        return None

    def perform_conversion(self, to_fmt):
        selected_ids = self.gui.library_view.get_selected_ids()

        if not selected_ids:
            error_dialog(self.gui, "No books selected", "Select a single book to enable conversion", show=True)
            return

        if len(selected_ids) > 1:
            error_dialog(self.gui, "Multiple books selected", "Select a single book to enable conversion", show=True)
            return

        book_id = selected_ids[0]

        input_format = self.kfx_format(book_id)
        if not input_format:
            error_dialog(self.gui, "Book does not contain KFX, KFX-ZIP, or KPF format", "Select a single book with KFX format for conversion", show=True)
            return

        if to_fmt in self.book_formats(book_id):
            if not question_dialog(
                    self.gui, "Format already present",
                    "<p>The book already contains %s format. If you proceed, it will be overwritten.<p>>Do you want to proceed?" % to_fmt.upper()):
                return

        wait_dialog = WaitDialog(self.gui, self.name, "Conversion in progress - please wait")
        db = self.gui.current_db.new_api
        input_file_name = db.format(book_id, input_format, as_file=False, as_path=True, preserve_filename=True)
        output_filename = None
        log = set_logger(GUILog2())
        msg = Message()

        try:
            self.report_version(log)
            log.info("")
            log.info("Processing %s" % input_file_name)
            book = YJ_Book(input_file_name, symbol_catalog_filename=get_symbol_catalog_filename())
            book.decode_book(retain_yj_locals=True)

            if to_fmt == "epub":
                try:
                    from calibre.ebooks.conversion.config import load_defaults
                    epub2_desired = load_defaults("epub_output").get("epub_version", "2") == "2"
                except Exception:
                    log.info("Failed to read default EPUB Output preferences")
                    epub2_desired = True

                epub_data = book.convert_to_epub(epub2_desired=epub2_desired)
                output_filename = PersistentTemporaryFile(".epub").name
                file_write_binary(output_filename, epub_data)
                log.info(msg("Converted book to EPUB"))

            elif to_fmt == "cbz":
                if book.is_image_based_fixed_layout:
                    cbz_data = book.convert_to_cbz()
                    output_filename = PersistentTemporaryFile(".cbz").name
                    file_write_binary(output_filename, cbz_data)
                    log.info(msg("Converted book images to CBZ"))
                else:
                    log.error(msg("Book format does not support CBZ conversion - must be image based fixed-layout"))

            if to_fmt == "pdf":
                if book.is_image_based_fixed_layout:
                    pdf_data = book.convert_to_pdf()
                    output_filename = PersistentTemporaryFile(".pdf").name
                    file_write_binary(output_filename, pdf_data)
                    log.info(msg("Extracted PDF content" if book.has_pdf_resource else "Converted book images to PDF"))
                else:
                    log.error(msg("Book format does not support PDF conversion - must be image based fixed-layout"))
            elif book.has_pdf_resource:
                log.warning("This book contains PDF content. Convert to PDF to extract it.")

            set_logger()
            wait_dialog.hide()

            if output_filename:
                info_dialog(self.gui, "Conversion Complete", msg.get(), det_msg=clean_log(log.html), show=True)
                db.add_format(book_id, to_fmt, output_filename, replace=True, run_hooks=False)      # add format

                # Update the gui view to reflect changes to the database
                self.gui.library_view.model().refresh_ids([id])
                current = self.gui.library_view.currentIndex()
                self.gui.library_view.model().current_changed(current, current)
                self.gui.tags_view.recount()
            else:
                error_dialog(self.gui, "Conversion Failed", msg.get(), det_msg=clean_log(log.html), show=True)

        except KFXDRMError:
            from calibre.gui2.dialogs.drm_error import DRMErrorMessage
            return DRMErrorMessage(self.gui).exec()

        except Exception as e:
            traceback.print_exc()
            error_dialog(
                self.gui, "Unhandled exception", repr(e),
                det_msg=clean_log(log.html) + add_text_to_html(repr(e)) + add_text_to_html(traceback.format_exc()),
                show=True)

        wait_dialog.hide()

    def report_version(self, log):
        try:
            platform_info = platform.platform()
        except Exception:
            platform_info = sys.platform     # handle failure to retrieve platform seen on linux

        log.info("Software versions: %s %s, calibre %s, %s" % (self.name, ".".join([str(v) for v in self.version]),
                 get_version(), platform_info))
        log.info("KFX Input plugin help is available at https://www.mobileread.com/forums/showthread.php?t=291290")

    def add_menu_action(self, menu, text, image=None, tooltip=None, triggered=None, enabled=True, submenu=None):
        # Minimal version without keyboard shortcuts, etc.

        ac = menu.addAction(text)

        if tooltip:
            ac.setToolTip(tooltip)
            ac.setStatusTip(tooltip)    # This is the only one actually used
            ac.setWhatsThis(tooltip)

        if triggered:
            ac.triggered.connect(triggered)

        if image:
            ac.setIcon(QIcon(I(image)))

        ac.setEnabled(enabled)

        if submenu:
            ac.setMenu(submenu)

        return ac

    def show_configuration(self):
        self.interface_action_base_plugin.do_user_config(self.gui)

    def show_help(self):
        open_url("https://www.mobileread.com/forums/showthread.php?t=291290")


class GUILog2(GUILog):
    def __init__(self):
        GUILog.__init__(self)
        self.outputs.append(ANSIStream())    # enable console output


class Message(object):
    def __init__(self):
        self.msg = ""

    def __call__(self, msg):
        self.msg = msg
        return msg

    def get(self):
        return self.msg


def clean_log(lg, wrap=True):
    # QT ignores text that looks like HTML tags such as <error>
    # fix HTML errors that prevent display of some messages. Leave spans since they are added by logger
    z = []
    for x in re.split("(<[^<]*)", lg):
        if x.startswith("<") and (not (x.startswith("<span") or x.startswith("</span"))):
            #print("strip: %s" % x)
            z.append("&lt;")
            z.append(x[1:])
        else:
            #print("keep: %s" % x)
            z.append(x)

    if wrap:
        return "<html><pre style=\"font-family: monospace\">" + ("".join(z)) + "</pre></html>"

    return "".join(z)


def add_text_to_html(text):
    return "<br/>" + html.escape(text).replace("\n", "<br/>")


class WaitDialog(QDialog):
    def __init__(self, parent, name, message):
        QDialog.__init__(self, parent)
        self.setWindowTitle(name)
        self.setWindowFlags(self.windowFlags() & (~Qt.WindowContextHelpButtonHint) & (~Qt.WindowCloseButtonHint))
        layout = QVBoxLayout()
        layout.addWidget(QLabel(message))
        self.setLayout(layout)
        self.setModal(True)
        self.show()

        for _ in range(200):
            time.sleep(0.001)
            QApplication.processEvents()    # hack to get "in progress" dialog to display
