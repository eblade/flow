import os

from ..needs import NeedsStomp
from ..base import EventBased


class GenericStompListener(EventBased, NeedsStomp):
    """
    Source class that listens for events on a Stomp URL.

    Options given under [Source]:

    .. code-block:: ini

        [Source]
        stomp url = <full stomp url>

    To use this with your flow daemon:

    .. code-block:: python

        from flow import Flow
        from flow.source import GenericStompListener

        class MyFlow(Flow):
            SOURCE = GenericStompListener

            def start(self, message):
                # message is a vizone.net.message_queue.Message
                pass
    """
    def __init__(self, stomp_url):
        self.stomp_url = os.path.expandvars(stomp_url)
        self.callback = None

    def run(self):
        self.stomp.register_handler(self.stomp_url, self.process_event)

    def process_event(self, event):
        if callable(self.callback):
            self.callback(event)
