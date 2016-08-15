=========
 Sources
=========

.. contents::


Introduction
============


Built-in Sources
================

Generic Stomp Listener
----------------------

.. autoclass:: flow.source.stomp.GenericStompListener
   :members:

Asset Entry Listener
--------------------

.. autoclass:: flow.source.asset.AssetEntryListener
   :members:

Unmanaged Files Listener
------------------------

.. autoclass:: flow.source.location.UnmanagedFilesListener
   :members:

STDIN
-----

.. autoclass:: flow.source.local.STDIN
   :members:

Interval
--------

.. autoclass:: flow.source.interval.Interval
   :members:

Building a Web Interface
========================

This is an example of a web interface built with Flow. The advantages of using Flow
for this are:

* Easy to configure.
* The worker pool can be used to handle asyncronous jobs.

It's recommended to use bottle since it's part of the python-one package but any other
framework can be used. This example features bottle however:


.. code-block:: python

    from flow import Flow, EventBased
    from flow.needs import NeedsClient
	from vizone.resource.asset import get_asset_by_id
    from one_depends import bottle

	class Web(EventBased, NeedsClient):
		_has_event_loop = True  # This prevents Flow from running a second
                                # event loop when bottle.run() exists.
		instance = None

		def __init__(self, interface='localhost', port=8080):
			self.server_interface = interface
			self.server_port = int(port)
			self.callback = None

			logging.log("Web Interface Settings", {
				'interface': self.server_interface,
				'port': self.server_port,
			}, 'pp')

			Web.instance = self  # We use this instance as a singleton 

		def run(self):
			bottle.run(
				host=self.server_interface,
				port=self.server_port,
			)


	class XmlServer(Flow):
		SOURCE = Web
    
        # this class could also implement the run(message) method and act
        # as a worker pool. The web method would then call
        # Web.interface.callback(message) to spawn a job. If a worker pool
        # is not needed, just leave this class like implemented here.


	@bottle.get('/<asset_id>')
	def get_asset(asset_id):
        """
        Serve XML for a given asset id.
        """
        try:
            asset = get_asset_by_id(asset_id, client=Web.instance.client)
        except HTTPClientError:
            return bottle.HttpError(status=404, body="There is no such asset.")
        
        bottle.response.status = 200
        bottle.response.set_header('Content-Type', asset.content_type)
        bottle.response.set_header('Content-Disposition', 'attachment; filename="%s.xml"' % asset.id)
        return output.generate()


And the corresponding INI file:

.. code-block:: ini

    [Flow]
    app name = xmlserver
    class = xmlserver.XmlServer

    [Source]
    interface = localhost
    port = 34566

    [Viz One]
    hostname = vizoneserver
    username = user
    password = password
    use https = no
    check certificates = no

