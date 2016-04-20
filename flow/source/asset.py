from vizone import logging
from vizone.opensearch import FeedIterator
from vizone.resource.asset import get_assets
from vizone.payload.asset import Item

from ..base import EventBased
from ..needs import NeedsClient, NeedsStomp


class AssetEntryListener(EventBased, NeedsClient, NeedsStomp):
    """
    Source class that listens for Asset Entry events. Make sure to
    have the Asset/Admin permission or it won't work.

    Options given under [Source]:

        None

    To use this with your flow daemon:

    from flow import Flow
    from flow.event import AssetEntryListener

    class MyFlow(Flow):
        SOURCE = AssetEntryListener

        def start(self, asset, info=None, log_id=-1):
            # asset is a vizone.payload.asset.Item
            # info contains the header
            # log_id is a unique number for the process spawned for this event
            pass
    """
    def __init__(self):
        self.callback = None

    def run(self):
        stomp_url = _get_asset_stomp_url(self.client)
        self.stomp.register_handler(stomp_url, self.process_asset_event)

    def process_asset_event(self, event):
        asset = Item(event)
        logging.info('(*) Event for asset %s "%s"', asset.id, asset.title)
        if callable(self.callback):
            self.callback(asset, event.headers)


def _get_asset_stomp_url(client): 
    assets = get_assets()
    if assets.monitor_link is not None:
        return assets.monitor_link.href
    else:
        raise ValueError("Asset feed has no monitor link. Are you admin?")
