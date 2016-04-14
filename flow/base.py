class Flow(object):
    """
    Base class for all flow workers. Do inherit this.
    """
    def __init__(self, instance_name=None):
        self.instance_name = instance_name

class Once(object):
    """
    Inherit this if you want to bypass parallelisation and not run as a daemon.
    """
    pass
