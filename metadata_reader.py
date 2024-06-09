from __future__ import (unicode_literals, division, absolute_import, print_function)

from calibre.customize import MetadataReaderPlugin

__license__ = "GPL v3"
__copyright__ = "2017-2024, John Howell <jhowell@acm.org>"


class KFXMetadataReader(MetadataReaderPlugin):
    name = "KFX metadata reader (from KFX Input)"
    description = "Read metadata from monolithic KFX files and KFX-ZIP archives"
    supported_platforms = ["windows", "osx", "linux"]
    file_types = {"azw8", "kfx", "kfx-zip", "kpf"}
    author = "jhowell"
    minimum_calibre_version = (5, 0, 0)

    def get_metadata(self, stream, ftype):
        from calibre_plugins.kfx_input.kfxlib import (set_logger, YJ_Book)
        from calibre.ebooks.metadata.book.base import Metadata
        from calibre.utils.logging import Log
        from calibre.utils.date import parse_only_date

        log = set_logger(Log())

        filename = stream.name if hasattr(stream, "name") else "stream"
        log.info("%s activated for %s" % (self.name, filename))

        md = YJ_Book(stream).get_metadata()
        set_logger()

        if not md.title:
            md.title = "Unknown"

        if md.cde_content_type == "EBSP":
            md.title += " - Sample"

        if not md.authors:
            md.authors.append("Unknown")

        mi = Metadata(md.title, md.authors)

        if md.asin:
            mi.set_identifiers({"mobi-asin": md.asin})

        if md.cover_image_data:
            mi.cover_data = md.cover_image_data

        if md.description:
            mi.comments = md.description

        if md.language:
            mi.language = md.language

        if md.issue_date:
            mi.pubdate = parse_only_date(md.issue_date, assume_utc=True)

        if md.publisher:
            mi.publisher = md.publisher

        #if md.asset_id:
        #    log.info("asset_id: %s" % md.asset_id)

        return mi
