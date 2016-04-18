from ..needs import NeedsStomp
from ..base import EventBased


class GenericStompListener(EventBased, NeedsStomp):
    """
    Source class that listens for events on a Stomp URL.

    Options given under [Source]:

        stomp url = <full stomp url>

    To use this with your flow daemon:

    from flow import Flow
    from flow.source.stomp import GenericStompListener

    class MyFlow(Flow):
        SOURCE = GenericStompListener

        def start(self, message, info=None, log_id=-1):
            # message is a vizone.net.message_queue.Message
            # info contains configuration as a hash
            # log_id is a unique number for the process spawned for this event
            pass
    """
    def __init__(self, stomp_url):
        self.stomp_url = stomp_url
        self.callback = None
        self.info = {'stomp url': stomp_url}

    def run(self):
        self.stomp.register_handler(self.stomp_url, self.process_event)

    def process_event(self, event):
        if callable(self.callback):
            self.callback(event, self.info)
