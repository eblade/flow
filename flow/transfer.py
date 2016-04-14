from . import Flow
from .needs import NeedsClient
from .source.local import STDIN


class TransferPlugin(Flow, NeedsClient):
    """
    Transfer Plugin base class.
    """
    SOURCE = STDIN

    def use(self, data):
        """
        Extract and verify the plugin data that comes from the Transfer Subsystem. We
        should have gotten two FTP addresses, plugin settings in the form of a VDF
        payload containing username and password, as well as a transfer step and
        request to control the workflow and report back progress.

        TransferPlugin child classes automatically inherits Flow and NeedsClient.
        """
        self.source = data.sourceurl
        assert self.source

        self.destination = data.destinationurl
        assert self.destination

        self.asset = data.asset
        assert self.asset is not None

        self.settings = data.pluginmetadata
        assert self.settings is not None

        self.step = data.transferstep
        assert self.step is not None

        self.request = data.transferrequest
        assert self.request is not None

        # Use provided credentials
        self.client.session.auth = (
            self.settings.get('plugin.user'),
            self.settings.get('plugin.password')
        )

    def update_progress(self, progress):
        self.step.progress.done = progress
        self.step.state.state = 'active'
        self.client.PUT(self.step.edit_link, self.step)

    def fail(self, message):
        self.step.state.state = 'error'
        self.step.error = message
        self.client.PUT(self.step.edit_link, self.step)
        exit(0)

    def start(self, data, **kwargs):
        raise NotImplemented
