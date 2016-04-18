from flow.transfer import TransferPlugin
from vizone.net.ftp import FXP, ftp_write
from vizone import logging


class XmlExport(TransferPlugin):
    """
    XML + Media Export Transfer Plugin.
    """

    def start(self, data, **kwargs):
        self.use(data)

        if self.asset.describedby_link.metadata is None:
            self.fail("Asset has no metadata")

        self.update_progress(0)

        loggin.info("Media source:      %s", self.source)
        loggin.info("Media destination: %s", self.destination)
        loggin.info("Setting up FXP...")

        fxp = FXP(self.source, self.destination, debug=True)

        loggin.info("FXP copying...")

        fxp.run()
        fxp.quit()

        loggin.log("FXP done", None, 'ok')

        self.update_progress(95)

        xml_destination = self.destination + ".xml"

        loggin.info("XML Destination:   %s", xml_destination)
        loggin.info("Writing metadata...")

        ftp_write(asset.describedby_link.metadata.generate())

        loggin.log("Metadata done", None, 'ok')

        self.update_progress(100)
