from . import Flow
from .needs import NeedsClient
from .source.local import STDIN


class TransferPlugin(Flow, NeedsClient):
    """
    Transfer Plugin base class.

    TransferPlugin child classes automatically inherits Flow and NeedsClient.

    Very basic example (for more advanced ones, look at the XmlExport built-ins):

    .. code-block:: python

        from flow.transfer import TransferPlugin
        from vizone import logging

        class MyTransferPlugin(TransferPlugin):
            def start(self, plugin_data):
                self.use(plugin_data)

                self.update_progress(0)

                logging.info(u'Asset is %s', self.asset.title)
                logging.info(u'Source URL is %s', self.source)
                logging.info(u'Destination URL is %s', self.destination)

                self.update_progress(100)

                # or why not:

                self.fail("There were errors!")
    """
    SOURCE = STDIN

    def use(self, data, require_asset=True, require_source=True, require_destination=True):
        """
        Extract and verify the plugin data that comes from the Transfer Subsystem. We
        should have gotten two FTP addresses, plugin settings in the form of a VDF
        payload containing username and password, as well as a transfer step and
        request to control the workflow and report back progress.

        You can use the ``require_asset``, ``require_source`` and ``require_metadata``
        flags to control what to require in terms of content in the plugin data.
        """

        self.step = data.transferstep
        assert self.step is not None, 'Missing transfer step payload'

        self.request = data.transferrequest
        assert self.request is not None, 'Missing transfer request payload'

        self.settings = data.pluginmetadata
        assert self.settings is not None, 'Missing plugin metadata'

        # Use provided credentials
        self.client.session.auth = (
            self.settings.get('plugin.user'),
            self.settings.get('plugin.password')
        )

        try:
            self.source = data.sourceurl
            if require_source:
                assert self.source, 'Missing source'

            self.destination = data.destinationurl
            if require_destination:
                assert self.destination, 'Missing destination'

            self.asset = data.asset
            if require_asset:
                assert self.asset is not None, 'Missing asset'

        except AssertionError as e:
            self.fail(e.message)


    def update_progress(self, progress):
        """
        Update the progress of the associated Transfer Step.

        Args:
            progress int: As a percentage from 0 to 100, e.g. 67
        """
        self.step.progress.done = progress
        self.step.state.state = 'active'
        self.client.PUT(self.step.edit_link, self.step)

    def fail(self, message):
        """
        Failed the Transfer Step and exits the program with status 0.
        This allows for a cleaner reporting in Viz One.

        Args:
            message unicode|str: An error message that will show up
                                 in Viz One.
        """
        self.step.state.state = 'error'
        self.step.error = message
        self.client.PUT(self.step.edit_link, self.step)
        exit(0)

    def start(self, data, **kwargs):
        """
        You'll have to implement this method yourself.
        """
        raise NotImplemented
