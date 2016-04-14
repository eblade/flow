import sys
from vizone import logging
from vizone.classutils import to_class

from .. import Once


class STDIN(Once):
    """
    Source class that reads standard in, designed to be run once, and especially
    for Transfer Plugins.

    Options given under [Source]:

        payload class = None|vizone.payload.transfer.PluginData|...

    To use this with your flow daemon:

    from flow import Flow
    from flow.event.local import STDIN

    class MyFlow(Flow):
        SOURCE = STDIN

        def start(self, data, **kwargs):
            # data is a vizone.payload.transfer.PluginData if that format is
            # chosen, else if raw it will be a unicode string
            # other kwargs are not used in this context
            pass
    """

    def __init__(self, payload_class=None):
        self.callback = None
        self.payload_class = to_class(payload_class)

    def run(self):
        data = self.read_plugin_data()
        if callable(self.callback):
            self.callback(data)
    
    def read_plugin_data(self):
        return self.payload_class(sys.stdin.read())
