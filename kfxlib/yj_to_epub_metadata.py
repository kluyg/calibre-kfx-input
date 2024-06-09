from __future__ import (unicode_literals, division, absolute_import, print_function)

import datetime

from .message_logging import log
from .yj_to_epub_properties import (
        DEFAULT_DOCUMENT_FONT_FAMILY, DEFAULT_FONT_NAMES, DEFAULT_DOCUMENT_FONT_SIZE,
        DEFAULT_DOCUMENT_LINE_HEIGHT, DEFAULT_KC_COMIC_FONT_SIZE)
from .yj_structure import (METADATA_NAMES, SYM_TYPE)


__license__ = "GPL v3"
__copyright__ = "2016-2024, John Howell <jhowell@acm.org>"


ORIENTATIONS = {
    "$385": "portrait",
    "$386": "landscape",
    "$349": "none",
    }


class KFX_EPUB_Metadata(object):
    def __init__(self):
        self.cover_resource = None
        self.is_print_replica = False
        self.is_pdf_backed = False
        self.is_pdf_backed_fixed_layout = False
        self.cde_content_type = ""
        self.nmdl_template_id = None

    def process_document_data(self):
        document_data = self.book_data.pop("$538", {})

        if "$433" in document_data:
            orientation_lock_ = document_data.pop("$433")
            if orientation_lock_ in ORIENTATIONS:
                self.orientation_lock = ORIENTATIONS[orientation_lock_]
            else:
                log.error("Unexpected orientation_lock: %s" % orientation_lock_)
                self.orientation_lock = "none"
        else:
            self.orientation_lock = "none"

        if "$436" in document_data:
            selection = document_data.pop("$436")
            if selection not in ["$442", "$441"]:
                log.error("Unexpected document selection: %s" % selection)

        if "$477" in document_data:
            spacing_percent_base = document_data.pop("$477")
            if spacing_percent_base != "$56":
                log.error("Unexpected document spacing_percent_base: %s" % spacing_percent_base)

        if "$581" in document_data:
            pan_zoom = document_data.pop("$581")
            if pan_zoom != "$441":
                log.error("Unexpected document pan_zoom: %s" % pan_zoom)

        if "$665" in document_data:
            self.set_book_type("comic")
            comic_panel_view_mode = document_data.pop("$665")
            if comic_panel_view_mode != "$666":
                log.error("Unexpected comic panel view mode: %s" % comic_panel_view_mode)

        if "$668" in document_data:
            auto_contrast = document_data.pop("$668")
            if auto_contrast != "$573":
                log.error("Unexpected auto_contrast: %s" % auto_contrast)

        document_data.pop("$597", None)

        document_data.pop("yj.semantics.book_theme_metadata", None)

        document_data.pop("yj.semantics.containers_with_semantics", None)

        document_data.pop("yj.semantics.page_number_begin", None)

        document_data.pop("yj.print.settings", None)
        document_data.pop("yj.authoring.auto_panel_settings_auto_mask_color_flag", None)
        document_data.pop("yj.authoring.auto_panel_settings_mask_color", None)
        document_data.pop("yj.authoring.auto_panel_settings_opacity", None)
        document_data.pop("yj.authoring.auto_panel_settings_padding_bottom", None)
        document_data.pop("yj.authoring.auto_panel_settings_padding_left", None)
        document_data.pop("yj.authoring.auto_panel_settings_padding_right", None)
        document_data.pop("yj.authoring.auto_panel_settings_padding_top", None)
        document_data.pop("yj.dictionary.text", None)

        document_data.pop("yj.conversion.source_attr_width", None)

        self.reading_orders = document_data.pop("$169", [])

        self.nmdl_template_id = document_data.pop("nmdl.template_id", None)
        if self.nmdl_template_id is not None and (
                len(self.reading_orders) != 2 or
                self.reading_orders[1].get("$178", "") != "note_template_collection" or
                self.nmdl_template_id not in self.reading_orders[1]["$170"]):
            log.error("note_template_collection reading order does not contain nmdl.template_id %s" % self.nmdl_template_id)
            log.info("reading orders: %s" % repr(self.reading_orders))

        if "max_id" in document_data:
            max_id = document_data.pop("max_id")
            if self.book_symbol_format != SYM_TYPE.SHORT:
                log.error("Unexpected document_data max_id=%s for %s symbol format" % (max_id, self.book_symbol_format))
        elif self.book_symbol_format == SYM_TYPE.SHORT and self.reading_orders and len(self.reading_orders[0].get("$170")) > 0:
            log.error("Book has %s symbol format without document_data max_id" % self.book_symbol_format)

        self.font_name_replacements["default"] = DEFAULT_DOCUMENT_FONT_FAMILY

        doc_style = self.process_content_properties(document_data)

        column_count = doc_style.pop("column-count", "auto")
        if column_count != "auto":
            log.warning("Unexpected document column_count: %s" % column_count)

        self.page_progression_direction = doc_style.pop("direction", "ltr")

        self.default_font_family = doc_style.pop("font-family", DEFAULT_DOCUMENT_FONT_FAMILY)

        for default_name in DEFAULT_FONT_NAMES:
            for font_family in self.default_font_family.split(","):
                self.font_name_replacements[default_name] = self.strip_font_name(font_family)

        self.default_font_size = doc_style.pop("font-size", DEFAULT_DOCUMENT_FONT_SIZE)
        if self.default_font_size not in [DEFAULT_DOCUMENT_FONT_SIZE, DEFAULT_KC_COMIC_FONT_SIZE]:
            log.warning("Unexpected document font-size: %s" % self.default_font_size)

        self.default_line_height = doc_style.pop("line-height", DEFAULT_DOCUMENT_LINE_HEIGHT)
        if self.default_line_height != DEFAULT_DOCUMENT_LINE_HEIGHT:
            log.warning("Unexpected document line-height: %s" % self.default_line_height)

        self.writing_mode = doc_style.pop("writing-mode", "horizontal-tb")
        if self.writing_mode not in ["horizontal-tb", "vertical-lr", "vertical-rl"]:
            log.warning("Unexpected document writing-mode: %s" % self.writing_mode)

        if self.writing_mode.endswith("-rl"):
            self.page_progression_direction = "rtl"

        self.check_empty(doc_style.properties, "document data styles")
        self.check_empty(document_data, "$538")

    def process_content_features(self):
        content_features = self.book_data.pop("$585", {})

        for feature in content_features.pop("$590", []):
            key = "%s/%s" % (feature.pop("$586", ""), feature.pop("$492", ""))
            version_info = feature.pop("$589", {})
            version = version_info.pop("version", {})
            version.pop("$587", "")
            version.pop("$588", "")

            self.check_empty(version_info, "content_features %s version_info" % key)
            self.check_empty(feature, "content_features %s feature" % key)

        if content_features.pop("$598", content_features.pop("$155", "$585")) != "$585":
            log.error("content_features id/kfx_id is incorrect")

        self.check_empty(content_features, "$585")

    def process_metadata(self):
        book_metadata = self.book_data.pop("$490", {})

        for categorised_metadata in book_metadata.pop("$491", []):
            category = categorised_metadata.pop("$495")
            for metadata in categorised_metadata.pop("$258"):
                key = metadata.pop("$492")
                self.process_metadata_item(category, key, metadata.pop("$307"))
                self.check_empty(metadata, "categorised_metadata %s/%s" % (category, key))

            self.check_empty(categorised_metadata, "categorised_metadata %s" % category)

        self.check_empty(book_metadata, "$490")

        for key, value in self.book_data.pop("$258", {}).items():
            self.process_metadata_item("", METADATA_NAMES.get(key, str(key)), value)

        if (self.book_type is None and self.fixed_layout and
                (self.virtual_panels_allowed or not self.is_print_replica)):
            self.set_book_type("comic")

            if not self.region_magnification:
                self.virtual_panels_allowed = True

        if self.book.is_scribe_notebook:
            self.fixed_layout = True
            self.set_book_type("notebook")
            if not self.title:
                self.title = "Notebook %s %s" % (self.book_id, datetime.date.today().isoformat())

    def process_metadata_item(self, category, key, value):
        cat_key = "%s/%s" % (category, key) if category else key

        if cat_key == "kindle_title_metadata/ASIN" or cat_key == "ASIN":
            if not self.asin:
                self.asin = value
        elif cat_key == "kindle_title_metadata/author":
            if value:
                self.authors.insert(0, value)
        elif cat_key == "kindle_title_metadata/author_pronunciation":
            if value:
                self.author_pronunciations.insert(0, value)
        elif cat_key == "author":
            if not self.authors:
                self.authors = [a.strip() for a in value.split("&") if a]
        elif cat_key == "kindle_title_metadata/book_id":
            self.book_id = value
        elif cat_key == "kindle_title_metadata/cde_content_type" or cat_key == "cde_content_type":
            self.cde_content_type = value
            if value == "MAGZ":
                self.set_book_type("magazine")
            elif value == "EBSP":
                self.is_sample = True
        elif cat_key == "kindle_title_metadata/description" or cat_key == "description":
            self.description = value.strip()
        elif cat_key == "kindle_title_metadata/cover_image":
            self.cover_resource = value
        elif cat_key == "cover_image":
            self.cover_resource = value
        elif cat_key == "kindle_title_metadata/dictionary_lookup":
            self.is_dictionary = True
            self.source_language = value.pop("$474")
            self.target_language = value.pop("$163")
            self.check_empty(value, "kindle_title_metadata/dictionary_lookup")
        elif cat_key == "kindle_title_metadata/issue_date":
            self.pubdate = value
        elif cat_key == "kindle_title_metadata/language" or cat_key == "language":
            self.language = self.fix_language(value)
        elif cat_key == "kindle_title_metadata/periodicals_generation_V2":
            self.set_book_type("magazine")
            self.virtual_panels_allowed = True
        elif cat_key == "kindle_title_metadata/publisher" or cat_key == "publisher":
            self.publisher = value.strip()
        elif cat_key == "kindle_title_metadata/title" or cat_key == "title":
            if not self.title:
                self.title = value.strip()
        elif cat_key == "kindle_title_metadata/title_pronunciation":
            if not self.title_pronunciation:
                self.title_pronunciation = value.strip()
        elif cat_key == "kindle_ebook_metadata/book_orientation_lock":
            if value != self.orientation_lock:
                log.error("Conflicting orientation lock values: %s, %s" % (self.orientation_lock, value))
            self.orientation_lock = value
        elif cat_key == "kindle_title_metadata/is_dictionary":
            self.is_dictionary = value
        elif cat_key == "kindle_title_metadata/is_sample":
            self.is_sample = value
        elif cat_key == "kindle_title_metadata/override_kindle_font":
            self.override_kindle_font = value
        elif cat_key == "kindle_capability_metadata/continuous_popup_progression":
            self.virtual_panels_allowed = True
            if value == 0:
                self.set_book_type("comic")
            elif value == 1:
                self.set_book_type("children")
        elif cat_key == "kindle_capability_metadata/yj_fixed_layout":
            self.fixed_layout = True
            if value == 1:
                pass
            elif value == 2:
                self.is_pdf_backed = True
                self.is_print_replica = True
            elif value == 3:
                self.is_pdf_backed = True
                self.is_pdf_backed_fixed_layout = True
                self.virtual_panels_allowed = True
        elif cat_key == "kindle_capability_metadata/yj_forced_continuous_scroll":
            self.scrolled_continuous = True
        elif cat_key == "kindle_capability_metadata/yj_guided_view_native":
            self.guided_view_native = True
        elif cat_key == "kindle_capability_metadata/yj_publisher_panels":
            self.set_book_type("comic")
            self.region_magnification = True
        elif cat_key == "kindle_capability_metadata/yj_facing_page":
            self.set_book_type("comic")
        elif cat_key == "kindle_capability_metadata/yj_double_page_spread":
            self.set_book_type("comic")
        elif cat_key == "kindle_capability_metadata/yj_textbook":
            self.is_pdf_backed = True
            self.is_print_replica = True
        elif cat_key == "kindle_capability_metadata/yj_illustrated_layout":
            self.illustrated_layout = self.html_cover = True
        elif cat_key == "reading_orders":
            if not self.reading_orders:
                self.reading_orders = value
        elif cat_key == "support_landscape":
            if value is False and self.orientation_lock == "none":
                self.orientation_lock = "portrait"
        elif cat_key == "support_portrait":
            if value is False and self.orientation_lock == "none":
                self.orientation_lock = "landscape"
