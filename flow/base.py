class Flow(object):
    """
    For worker classes.

    Base class for all flow workers. Do inherit this.
    """
    def __init__(self, instance_name=None):
        self.instance_name = instance_name


class Once(object):
    """
    For Source classes.

    Inherit this if you want to bypass parallelisation and not run as a daemon.
    """
    pass


class Iterable(object):
    """
    For Source classes.

    Inherit this if you want Flow to run your source's run method keeping the
    workers busy. The typical use case is that you have a large set of tasks
    to go through and you want to use a worker pool to accomplish them.

    Your Source class must implement the next() method, which should return an
    (object, infohash) tuple and raise StopIteration when exhausted.
    """
    def __iter__(self):
        return self

    def next(self):
        raise NotImplemented


class EventBased(object):
    pass
