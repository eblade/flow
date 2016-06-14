from flow.transfer import TransferPlugin
from vizone.net.ftp import FXP, ftp_write, connect
from vizone import logging


class XmlExportFXP(TransferPlugin):
    """
    XML + Media Export Transfer Plugin using FXP.
    """

    def start(self, data):
        # Parse the PluginData
        self.use(data)

        # Verfify that we have metadata (otherwise this plugin makes little sense)
        if self.asset.describedby_link.metadata is None:
            self.fail("Asset has no metadata")

        # Set the progress to 0 (this will show an empty progress bar in Studio)
        self.update_progress(0)

        logging.info("Media source:      %s", self.source)
        logging.info("Media destination: %s", self.destination)
        logging.info("Setting up FXP...")

        # Set up an FXP transfer (what is FXP? see
        # https://en.wikipedia.org/wiki/File_eXchange_Protocol)
        fxp = FXP(self.source, self.destination, debug=True)
        loggin.info("FXP copying...")
        fxp.run()
        fxp.quit()
        logging.log("FXP done", None, 'ok')

        # Update the progress to 99%, we're not there yet
        self.update_progress(99)

        # Construct a xml destiniation path
        xml_destination = self.destination + ".xml"
        logging.info("XML Destination:   %s", xml_destination)
        logging.info("Writing metadata...")

        # Write the Asset Metadata to the xml destination path
        ftp_write(xml_destination, asset.describedby_link.metadata.generate())
        loggin.log("Metadata done", None, 'ok')

        # Set the progress to 100% and we're done
        self.update_progress(100)


class XmlExportArdFTP(TransferPlugin):
    """
    XML + Media Export Transfer Plugin using ArdFTP SITE commands.
    """

    def start(self, data):
        # Parse the PluginData
        self.use(data)

        # Verfify that we have metadata (otherwise this plugin makes little sense)
        if self.asset.describedby_link.metadata is None:
            self.fail("Asset has no metadata")

        # Set the progress to 0 (this will show an empty progress bar in Studio)
        self.update_progress(0)

        logging.info("Media source:      %s", self.source)
        logging.info("Media destination: %s", self.destination)
        logging.info("Setting up FTP...")

        # Connect to the source FTP server
        ftp, source_path = connect(self.source, debug=True)
        source_filename = os.path.basename(source_path)
        source_directory = os.path.dirname(source_path)

        # Here you can also run other SITE commands before starting the transfer

        # Set up ArdFTP for copying the media file (you might have to use other
        # settings)
        ftp.voidcmd('SITE ARDENDO FORMAT MXF')
        ftp.voidcmd('SITE ARDENDO USE MXF %s' % source_filename)
        ftp.voidcmd('SITE ARDENDO STOR %s' % self.destination)

        # This "downloads" a status file from the source FTP server, containing
        # information about percentage done of the transfer. This is the main
        # advantage compared to using FXP
        ftp.retrlines('RETR status.log', callback=self.read_status)

        # When that transfer is finished, so is the media transfer and we may
        # close the connection to the source FTP server.
        ftp.quit()
        logging.log(u'FTP done', None, 'ok')

        # Now let's adjust the progress, we're not quite done yet
        self.update_progress(99)

        # Construct a xml destiniation path
        xml_destination = self.destination + ".xml"
        loggin.info("XML Destination:   %s", xml_destination)
        loggin.info("Writing metadata...")

        # Write the Asset Metadata to the xml destination path
        ftp_write(xml_destination, asset.describedby_link.metadata.generate())
        loggin.log("Metadata writing done", None, 'ok')

        # Set the progress to 100% and we're done
        self.update_progress(100)

    def read_status(self, status_line):
        try:
            logging.log('Status line', status_line, 'info')
            if '%' in status_line:
                with_percent, rest = status_line.split('%', 1)
                status, value = with_percent.split(' ')
                self.update_progress(value)
        except e:
            logging.error("Error parsing status line from arftp: " + str(e))
