from flow import Flow
from flow.source import Interval

from vizone import logging


class IntervalStub(Flow):
    SOURCE = Interval

    def start(self, message):
        logging.info('Got callback.')
