import sys
from vizone import logging
from vizone.classutils import to_class

from .. import Once


class STDIN(Once):
    """
    Source class that reads standard in, designed to be run once, and especially
    for Transfer Plugins.

    Options given under [Source]:

    .. code-block:: ini

        [Source]
        payload class = None|vizone.payload.transfer.PluginData|...

    To use this with your flow daemon:

    .. code-block:: python

        from flow import Flow
        from flow.source.local import STDIN

        class MyFlow(Flow):
            SOURCE = STDIN

            def start(self, data):
                # data is a vizone.payload.transfer.PluginData if that format is
                pass
    """

    def __init__(self, payload_class=None):
        self.payload_class = to_class(payload_class)

    def run(self):
        return self.read_plugin_data()
    
    def read_plugin_data(self):
        return self.payload_class(sys.stdin.read())
