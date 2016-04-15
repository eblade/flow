from lxml import etree
from datetime import date, time, datetime

from flow import Flow
from flow.needs import NeedsStore, NeedsClient, NeedsConfig
from flow.source import UnmanagedFilesListener
from flow.operation import (
    create_or_update_asset,
    delete_unmanaged_file,
    import_unmanaged_file,
)
from flow.lock import Locked
from flow.data import MultiParser

from vizone import logging
from vizone.iso8601 import Timestamp
from vizone.urilist import UriList
from vizone.payload.asset import Item
from vizone.payload.metadata import ImportExport


class XmlImport(Flow, NeedsClient, NeedsStore, NeedsConfig):
    """
    XML + Media Importer using the Unmanaged File API.

    - If an XML file comes in, it will be read as an Import/Export payload and
      a Placeholder will be created (or updated if id is given and an asset
      with that id exists).

    - If a non-XML file comes in, it will be considered "media".

    - If this "media" is mentioned by some read Import/Export payload, it will
      be imported to it's Placeholder.

    - If this "media" is not mentioned yet, it will be remembered (server-side,
      using the Client Config API).

    - If an XML file comes in and mentiones a "media" that is "remembered", it
      will be imported to the Placeholder directly.

    - If an XML file comes in and references an Asset Entry that is no longer
      a Placeholder, the Metadata will be updated if changed.

    - If a non-XML comes in, and there is an occupied Asset Entry pointing to
      it, the import will fail.

    Example ini file for using this importer:

        [Flow]
        class = flow.daemon.xmlimport.XmlImport

        [Source]
        location = xmlimport
        skip empty files = no

    Note that the "skip empty files" option has the following effect:

        yes: Tail mode
        no: No tail mode

        [Xml]
        format = default|custom

    If you choose ``default`` here, the daemon will do a default Viz One XML Import
    based on the standard Import/Export format.

    On the other hand, if you want a custom XML to be imported you can choose
    ``custom`` and it will be parsed and mapped according to the following
    rules specified by these sections in the INI:

        [Namespaces]
        short = http://long/name
        ...

    Namespaces are optional. You will need to specify only the once used in the fields
    you want to parse.

        [Field:NAME]
        xpath = /path/to/value
        type = string|integer|date|time|datetime|dictionary
        format = formatstring for parsing dates

    For each field you want to parse, create one of these. For string fields, you only
    need the ``xpath``, since ``type`` defaults to ``string``. The value will be stored
    under the name NAME for later use with the mapper. Fields of type ``dictionary``
    will require a ``source`` argument, being an http link to the dictionary feed. Field
    of type ``datetime`` support a ``default timezone`` argument, which should be parsable
    by python; for instance ``Europe/Stockholm`` or ``GMT``.

        [Transform]
        NAME = EXPR
        compound_field = field1 + ':' + field2

    The ``Transform`` section allows for simple data transformation. The left-hand side
    denotes the name to store under and the right-hand side should contain a valid
    python expression using the names from ``Field`` directives and previous ``Transform``
    operations. They will be carried out in the order they are written.

        [Vdf]
        form = FORM
        asset.title = FIELD1
        asset.alternativeTItle = FIELD2
        ...

    Last is the actual mapping taking place, where you can put the stored data into VDF
    fields. Remember to specify the form here. The current revision is always used, you
    should not try to specify a revision.
    """

    SOURCE = UnmanagedFilesListener

    def configure(self, config):
        self.mappings = {}
        self.xml_format = config.get("Xml", "format")

        if self.xml_format == 'default':  # else custom
            return

        if config.has_section("Namespaces"):
            self.namespaces = {k: v for k, v in config.items("Namespaces")}
        else:
            self.namespaces = {}

        self.fields = {}
        for section in config.sections():
            if section.startswith("Field:"):
                fieldname = section[6:]
                field = Field(fieldname, **{k.replace(' ', '_'): v for k, v in config.items(section)})
                self.fields[fieldname] = field

        if config.has_section("Transforms"):
            self.transforms = config.items("Transforms")
        else:
            self.transforms = {}

        if config.has_section("Vdf"):
            self.vdf_mappings = {k: v for k, v in config.items("Vdf")}
        else:
            self.vdf_mappings = {}

    def start(self, f, info=None, log_id=-1):
        # Queue up multiple events for the same file
        with Locked(f.title):
            logging.info('(%i) Processing XML file %s.', log_id, f.title)

            if is_xml(f):  # XML file
                if f.media.filesize == 0:
                    logging.info('(%i) Skipping empty XML file %s.', log_id, f.title)
                    return

                # Extract and translate the metadata from the XML
                media_filename = None
                if self.xml_format == 'default':
                    xml = ImportExport(self.client.GET(f.media.url))
                    metadata= (xml.describedby_link.metadata
                               if xml.describedby_link is not None else None)
                    if xml.content and xml.content.src:
                        media_filename = xml.content.src
                    asset_id = xml.id

                # Custom Xml mode requires some further settings in the INI
                elif self.xml_format == 'custom':
                    r = self.client.GET(f.media.url)
                    asset_id, media_filename, metadata = self.custom_parse(f.title, r.content, log_id)

                # Create or Update a placeholder, including Metadata update from XML
                asset = create_or_update_asset(
                    id=asset_id,
                    metadata=metadata, # may be a vizone.vdf.Payload or a dict
                    client=self.client,
                    log_id=log_id,
                )

                # Remove the XML file, we're done with it
                delete_unmanaged_file(
                    unmanaged_file=f,
                    client=self.client,
                    log_id=log_id,
                )

                # Jump out here if this is not a placeholder
                if asset.assetmediatype != 'placeholder':
                    logging.info('(%i) Asset is not a placeholder, skip import.', log_id)
                    return

                # Check if a media file waas mentioned in atom:content/@src
                if media_filename:
                    logging.info('(%i) Wants media file %s.', log_id, media_filename)

                    # Check if we have a MIN for it already
                    stored_info = self.store.get(media_filename)
                    if stored_info is not None and stored_info.get('type') == 'media':

                        # Start the import
                        import_unmanaged_file(
                            asset,
                            UriList([stored_info.get('link')]),
                            client=self.client,
                            log_id=log_id,
                        )
                        self.store.delete(media_filename)
                    else:
                        logging.info('(%i) Remember media file %s -> asset %s.',
                                     log_id, media_filename, asset.id)
                        self.store.put(media_filename,
                                       {'type': 'asset', 'link': asset.self_link.href})

            else:  # Media file

                # Check if there is an XML that mentioned this media file
                stored_info = self.store.get(f.title)
                if stored_info is not None and stored_info.get('type') == 'asset':

                    # Fetch the asset and import to it
                    asset = Item(self.client.GET(stored_info.get('link')))
                    import_unmanaged_file(
                        asset,
                        UriList([f.self_link.href]),
                        client=self.client,
                        log_id=log_id,
                    )
                    self.store.delete(f.title)

                elif stored_info is None:
                    logging.info('(%i) Remember media file %s -> unmanaged file %s.',
                                 log_id, f.title, f.self_link.href)
                    self.store.put(f.title, {'type': 'media', 'link': f.self_link.href})

    def custom_parse(self, filename, xml_string, log_id):
        dom = etree.fromstring(xml_string)

        # Parsing
        data = {
            'xml_filename': filename,
        }
        for fieldname, field in self.fields.items():
            elements = dom.xpath(field.xpath, namespaces=self.namespaces)
            raw_value = elements[0] if len(elements) else None
            try:
                raw_value = raw_value.text
            except:
                pass
            data[fieldname] = field.get_value(raw_value, self.client)
        logging.log("(%i) Data" % log_id, data, 'pp')

        # Transforming
        for fieldname, expr in self.transforms:
            data[fieldname] = eval(expr, data)
        if '__builtins__' in data.keys():
            del data['__builtins__']
        logging.log("(%i) Data Post Transform" % log_id, data, 'pp')

        # Writing to VDF
        vdf = {}
        for fieldname, expr in self.vdf_mappings.items():
            vdf[fieldname] = eval(expr, data)

        logging.log("(%i) Vdf" % log_id, vdf, 'pp')
        media_filename = data.get('media_filename')
        asset_id = data.get('asset_id')
        return asset_id, media_filename, vdf


def is_xml(f):
    return f.title.lower().endswith('.xml')


class Field(object):
    def __init__(self, name, xpath=None, **kwargs):
        self.name = name
        self.xpath = xpath
        assert self.xpath is not None, "Field %s is missing an xpath" % self.name
        try:
            self._parser = MultiParser(**kwargs)
        except AssertionError as e:
            raise AssertionError(("Field %s:" % (self.name)) + str(e))

    def get_value(self, raw_value, client):
        return self._parser.convert(raw_value, client)
