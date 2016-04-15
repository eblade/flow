from threading import Lock


class LogId(object):
    """
    Thread-safe incrementer.
    
    Use like this:

        log_id = LogId()
        first_id = log_id.next()
        next_id = log_id.next()
        # ...
    """
    def __init__(self):
        self._count = 0
        self._lock = Lock()

    def next(self):
        self._lock.acquire()
        returned_id = self._count
        self._count += 1
        self._lock.release()
        return returned_id
