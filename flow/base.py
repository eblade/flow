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
    """
    For Source classes.

    Inherit this if you want Flow t orun your source's run method once, which
    initiates some kind of event listener. Upon event the source should call
    its callback, which will be spawing the start method on the worker as a
    new thread.

    Set ``_has_event_loop`` to ``True`` if your ``run`` method has it's own
    event loop. If ``False``, an event loop will be created by Flow.

    The source class does not have to call the ``callback()`` function but
    should do so for any asyncronous operations.
    """
    _has_event_loop = False
