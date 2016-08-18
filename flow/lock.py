from threading import Lock


_locks = {}
_internal_lock = Lock()


def _lock(key):
    with _internal_lock:
        lock = _locks.get(key) or Lock()

    lock.acquire()

    with _internal_lock:
        if not key in _locks:
            _locks[key] = lock


def _unlock(key):
    with _internal_lock:
        lock = _locks.get(key)

    if lock is None:
        return

    lock.release()

    with _internal_lock:
        if key in _locks:
            del _locks[key]


class Locked(object):
    """
    Thread-safe lock by key string.

    Usage:

    .. code-block:: python

        from flow.lock import Locked

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


