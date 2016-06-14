from vizone import logging
from vizone.opensearch import FeedIterator
from vizone.resource.unmanaged_file import get_unmanaged_files
from vizone.payload.media import UnmanagedFileCollection

from ..needs import NeedsClient, NeedsStomp
from ..base import EventBased


class UnmanagedFilesListener(EventBased, NeedsClient, NeedsStomp):
    """
    Source class that listens for UnmanagedFile events for a given location.

    Options given under [Source]:

    .. code-block:: ini

        [Source]
        location = <handle of an import storage>
        skip empty files = <yes/no>

    To use this with your flow daemon:

    .. code-block:: python

        from flow import Flow
        from flow.source import UnmanagedFilesListener

        class MyFlow(Flow):
            SOURCE = UnmanagedFilesListener

            def start(self, f):
                # f is a vizone.payload.media.UnmanagedFile
                pass
    """
    def __init__(self, location=None, skip_empty_files='no'):
        self.location = location
        self.skip_empty_files = skip_empty_files == 'yes'
        self.callback = None

    def run(self):
        stomp_url = _get_location_stomp_url_by_handle(self.location, self.client)
        self.stomp.register_handler(stomp_url, self.process_file_event)

    def process_file_event(self, event):
        unmanaged_files = UnmanagedFileCollection(event)
        for unmanaged_file in FeedIterator(unmanaged_files, self.client):
            logging.info('Event for unmanaged file "%s"', unmanaged_file.title)

            if self.skip_empty_files and unmanaged_file.media.filesize == 0:
                logging.info('Skipping empty file %s.', unmanaged_file.title)
                return

            if callable(self.callback):
                self.callback(unmanaged_file)


def _get_location_stomp_url_by_handle(handle, client): 
    locations = get_unmanaged_files()
    for location in locations.entries:
        if location.id == handle:
            ufc = UnmanagedFileCollection(client.GET(location.down_link))
            return ufc.monitor_link.href
    raise LookupError('No such location handle: "%s"' % handle)
