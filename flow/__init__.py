class Flow(object):
    def __init__(self, instance_name=None):
        self.instance_name = instance_name


class NeedsClient(object):
    def set_client(self, client):
        self.client = client


class NeedsStomp(object):
    def set_stomp(self, stomp):
        self.stomp = stomp
    

class NeedsStore(object):
    def set_store(self, store):
        self.store = store
    
