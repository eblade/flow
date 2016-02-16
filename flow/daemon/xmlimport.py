from flow import Flow, NeedsStore, NeedsClient
from flow.event import UnmanagedFilesListener
from flow.operation import (
    create_or_update_placeholder,
    delete_unmanaged_file,
    import_unmanaged_file,
)
from flow.util import Locked

from vizone import logging
from vizone.urilist import UriList
from vizone.payload.asset import Item
from vizone.payload.metadata.importexport import ImportExport


class XmlImport(Flow, NeedsClient, NeedsStore):
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
    """

    SOURCE = UnmanagedFilesListener

    def start(self, f, info=None, log_id=-1):

        # Queue up multiple events for the same file
        with Locked(f.title):
            logging.info('(%i) Processing XML file %s.', log_id, f.title)

            if is_xml(f):  # XML file
                if f.media.filesize == 0:
                    logging.info('(%i) Skipping empty XML file %s.', log_id, f.title)
                    return
                
                # Create or Update a placeholder, including Metadata update from XML
                xml = ImportExport(self.client.GET(f.media.url))
                asset = create_or_update_placeholder(
                    id=xml.id,
                    metadata=xml.describedby_link.metadata 
                             if xml.describedby_link is not None else None,
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
                if xml.content and xml.content.src:
                    logging.info('(%i) Wants media file %s.', log_id, xml.content.src)

                    # Check if we have a MIN for it already
                    stored_info = self.store.get(xml.content.src)
                    if stored_info is not None and stored_info.get('type') == 'media':

                        # Start the import
                        import_unmanaged_file(
                            asset,
                            UriList([stored_info.get('link')]),
                            client=self.client,
                            log_id=log_id,
                        )
                        self.store.delete(xml.content.src)
                    else:
                        logging.info('(%i) Remember media file %s -> asset %s.',
                                     log_id, xml.content.src, asset.id)
                        self.store.put(xml.content.src,
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


def is_xml(f):
    return f.title.lower().endswith('.xml')
