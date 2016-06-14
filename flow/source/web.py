from ..base import EventBased

try:
    import bottle
except ImportError:
    from one_depends import bottle

from vizone import logging


class WebInterface(EventBased):
    """
    Source class for Web Application.
    """
    def __init__(self, interface='localhost', port=8080, static_root=None):
        self._server_interface = interface
        self._server_port = int(port)
        self._server_static_root = static_root
        self.callback = None

        logging.log("Web Interface Settings", {
            'interface': self._server_interface,
            'port': self._server_port,
            'static root': self._server_static_root,
        }, 'pp')

        self.web = bottle.Bottle()

    def run(self):
        for name in dir(self):
            f = getattr(self, name)
            if callable(f):
                if f.__doc__ is not None:
                    doc = f.__doc__
                    doc = doc.split('\n')[0]
                    if doc.startswith('GET ') or \
                       doc.startswith('PUT ') or \
                       doc.startswith('POST ') or \
                       doc.startswith('DELETE '):

                        verb, path = doc.split(' ', 1)
                        self.web.route(path=path, method=verb.lower(), callback=f)

        self.web.run(
            host=self._server_interface,
            port=self._server_port,
        )

    def static_file(self, path):
        return bottle.static_file(path, root=self._server_static_root)
