from flow import Flow
from flow.needs import NeedsClient
from flow.source import GenericStompListener
from flow.lock import Locked

from vizone import logging
from vizone.payload.asset import Item


class StompStub(Flow, NeedsClient):
    SOURCE = GenericStompListener

    def start(self, message, info=None, log_id=-1):
        with Locked(asset.atomid):
            asset = Item(message)
            # do things with asset here
