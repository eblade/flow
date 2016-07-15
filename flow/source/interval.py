import time
import datetime

from vizone import logging

from .. import EventBased


class Interval(EventBased):
    """
    Source class that triggers an event on interval.

    Options given under [Source]:

    .. code-block:: ini

        [Source]
        interval = 60 (seconds)
        window start = 01:00 [HH[:MM[:SS]]]
        window end = 03:00 [HH[:MM[:SS]]]

    To use this with your flow daemon:

    .. code-block:: python

        from flow import Flow
        from flow.source import Interval

        class MyFlow(Flow):
            SOURCE = Interval

            def start(self, data):
                pass

    Note that data is always ``None`` for this source.
    """

    def __init__(self, interval=60, window_start=None, window_end=None):
        self.interval = int(interval)
        self.window_start = datetime.time(*[int(d) for d in window_start.split(':')]) \
                if window_start is not None else None
        self.window_end = datetime.time(*[int(d) for d in window_end.split(':')]) \
                if window_end is not None else None
        self.callback = None

        logging.info('Interval: %s seconds', self.interval)
        if self.window_start is not None:
            logging.info('Time window start: %s', self.window_start.isoformat())
        if self.window_end is not None:
            logging.info('Time window end: %s', self.window_end.isoformat())

    def run(self):
        last = None
        off = 0

        while True:
            now = datetime.datetime.now()
            sleep_time = 1.

            if last is None:
                diff = None

            else:
                diff = (now - last).total_seconds()

            if in_window(self.window_start, self.window_end, now):
                if diff is None or diff >= self.interval:
                    off = (diff or self.interval) - self.interval
                    logging.debug('On Interval (after %f seconds, off by %f).', diff or 0, off)
                    self.callback(None)
                    last = now
                else:
                    sleep_time = max(0.0001, min(1., self.interval - diff - off))

            time.sleep(sleep_time)


def in_window(start, end, now):
    now = now.time()

    if start is not None and end is not None:
        if start < end:
            return start <= now <= end
        else:
            return now >= start or now <= end
    
    elif start is not None:
        return now >= start

    elif end is not None:
        return now <= end

    else:
        return True
        
