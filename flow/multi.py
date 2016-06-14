import threading
import time
from vizone import logging


class Pool(object):
    def __init__(self, workers=1, join=True, timeout=60):
        logging.info("Create pool with %i workers (%s, timeout=%i).",
                     workers, 'join' if join else 'no join', timeout)
        self.start_time = time.time()

        self.worker_count = workers
        self.join = join
        self.timeout = timeout

        self.resource = threading.BoundedSemaphore(workers)

        self.threads_lock = threading.Lock()
        self.threads = {}

        self.counter_lock = threading.Lock()
        self.counter = 0
        self.avg_time = 0

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        logging.debug("Exit pool.")
        if self.join:
            for thread in self.threads.values():
                thread.join(self.timeout)
                logging.debug("Exit joined %s. (%s)", thread.name,
                        "timed out" if thread.is_alive() else "ok")
        total_time = time.time() - self.start_time
        logging.info("Ran %i tasks in %f seconds (avg %f seconds per task).",
                self.counter, total_time, self.avg_time)

    def _next_id(self, control=False):
        if not control:
            self.counter_lock.acquire()
            self.counter += 1
            self.counter_lock.release()
        return ("control_" if control else "worker_") + str(self.counter)

    def _control(self, thread):
        logging.debug("Start control thread for %s.", thread.name)
        start_time = time.time()
        thread.start()
        thread.join(self.timeout)
        end_time = time.time()
        logging.debug("Control thread joined %s. (%s)", thread.name,
                "timed out" if thread.is_alive() else "ok")
        self.counter_lock.acquire()
        self.avg_time = (self.avg_time + (end_time - start_time)) / 2
        self.counter_lock.release()
        self.threads_lock.acquire()
        del self.threads[thread.name]
        self.threads_lock.release()

        self.resource.release()
        logging.debug("Exit control thread for %s.", thread.name)

    def spawn(self, worker, *args, **kwargs):
        logging.debug("Start spawn.")
        self.resource.acquire()
        logging.debug("Acquired resource.")

        def with_local_log_id(worker):
            def wrapped(*args, **kwargs):
                try:
                    logger = kwargs.pop('logger')
                    log_id = kwargs.pop('log_id')
                    logger.set_log_id(log_id)
                except KeyError:
                    pass
                except AttributeError:
                    pass

                return worker(*args, **kwargs)

            return wrapped
        
        worker_thread = threading.Thread(
            target=with_local_log_id(worker),
            name=self._next_id(),
            args=args,
            kwargs=kwargs,
        )
        worker_thread.daemon = True

        control_thread = threading.Thread(
            target=self._control,
            name=self._next_id(control=True),
            args=(worker_thread, ),
        )
        control_thread.daemon = True

        self.threads_lock.acquire()
        self.threads[worker_thread.name] = control_thread
        self.threads_lock.release()

        logging.debug("Spawn starts control thread %s.", control_thread.name)
        control_thread.start()


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
        self._lock = threading.Lock()

    def next(self):
        self._lock.acquire()
        returned_id = self._count
        self._count += 1
        self._lock.release()
        return returned_id
