from gevent.coros import BoundedSemaphore


_locks = {}
_internal_lock = BoundedSemaphore(1)


def _lock(key):
    _internal_lock.acquire()
    lock = _locks.get(key) or BoundedSemaphore(1)
    lock.acquire()
    if not key in _locks:
        _locks[key] = lock
    _internal_lock.release()


def _unlock(key):
    _internal_lock.acquire()
    lock = _locks.get(key) or BoundedSemaphore(1)
    lock.release()
    if key in _locks:
        del _locks[key]
    _internal_lock.release()


class Locked(object):
    """
    Thread-safe lock by key string.

    Usage:

        with Locked('mystring'):
            # .. do stuff

    Only one process per key can be run simultaneously, other attempt
    will be held until the lock is released.
    """
    def __init__(self, key):
        self.key = key

    def __enter__(self):
        _lock(self.key)
        return self

    def __exit__(self, type, value, traceback):
        _unlock(self.key)


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
        self._semaphore = BoundedSemaphore(1)

    def next(self):
        self._semaphore.acquire()
        returned_id = self._count
        self._count += 1
        self._semaphore.release()
        return returned_id
