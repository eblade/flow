class NeedsClient(object):
    def set_client(self, client):
        self.client = client


class NeedsStomp(object):
    def set_stomp(self, stomp):
        self.stomp = stomp


class NeedsStore(object):
    def set_store(self, store):
        self.store = store


class NeedsConfig(object):
    def configure(self, config):
        raise NotImplemented("You must implement configure(self, ConfigParser)")


class NeedsCleanUp(object):
    def clean_up(self, config):
        raise NotImplemented("You must implement clean_up(self)")
