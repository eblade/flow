from flow import Flow
from flow.needs import NeedsStore, NeedsClient, NeedsConfig
from flow.source import AssetEntryListener
from flow.operation import retry_on_conflict, Retry

from vizone import logging
from vizone.client import HTTPClientError, HTTPServerError
from vizone.vdf import Payload

Payload._default_namespace = 'http://www.vizrt.com/types'
Payload._default_output_format = 'xml_alt'


class MetadataMapper(Flow, NeedsClient, NeedsStore, NeedsConfig):
    """
    Metadata-mapping daemon that reacts on Asset Entry updates.

    Example ini file:
        
    .. code-block:: ini

        [Flow]
        class = metadatamapper.MetadataMapper

        [Source]
        # AssetEntryListener has no configurable parameters

        [Mappings]
        asset.alternateTitle = metadata.get('asset.title') + ' alternative'
    """
    SOURCE = AssetEntryListener

    def configure(self, config):
        logging.info("Configure.")

        self.mappings = {}
        if config.has_section("Mappings"):
            self.mappings = {k: v for k, v in config.items("Mappings")}
        logging.log("Mappings", self.mappings, 'pp')

    @retry_on_conflict(max_retries=5)
    def start(self, asset, conflict=False):
        # Fetch metadata with a fresh etag
        try:
            old_metadata = Payload(self.client.GET(asset.describedby_link))

        # If no metadata is found, we cannot do any metadata mapping
        except HTTPClientError as e:
            logging.error(u'Asset Metadata fetching failed %s', str(e))
            return

        # If there was an internal server error (5xx), wait and retry
        except HTTPServerError as e:
            logging.error(u'Asset Metadata fetching failed %s', str(e))
            logging.warn(u'Retrying in 10 seconds...')
            time.sleep(10)
            raise Retry

        # Copy metadata and operate on the copy, so we can compare them later
        new_metadata = Payload(old_metadata.generate())
        scope = {
            'asset': asset,
            'metadata': new_metadata,
        }
        for field, expr in self.mappings.items():
            logging.info('%s = %s', field, expr)
            new_metadata.set(field, eval(expr, scope))

        logging.log(u'Resulting payload', new_metadata.generate(), 'xml')
        
        # Only update if we produced any differences, else we will have a circle of updates
        if new_metadata != old_metadata:
            logging.info(u'Updating metadata...')
            self.client.PUT(
                asset.describedby_link,
                new_metadata,
                etag=old_metadata.response_etag
            )
            logging.info(u'Updated metadata.')
        else:
            logging.info(u'No changes to metadata.')
