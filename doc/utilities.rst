=============
 Utililities
=============

.. contents::


Working with Assets
===================

Tools for working with Asset Entries (Items)

Create or Update Asset
----------------------

.. autofunction:: flow.operation.create_or_update_asset


Modifying Group Permissions in an ACL
-------------------------------------

.. autofunction:: flow.acl.set_group_permissions


Working with Files
==================

Tools useful for handling file import flows.

Import Unmanaged File
---------------------

.. autofunction:: flow.operation.import_unmanaged_file


Delete Unmanaged File
---------------------

.. autofunction:: flow.operation.delete_unmanaged_file


Building a Transfer Plugin
==========================

You can use Flow to build a Transfer Plugin quite easily.

Extending the TransferPlugin class
----------------------------------

.. autoclass:: flow.transfer.TransferPlugin
   :members:


Setting up the Repository
-------------------------

Creating a Transfer Plugin package is easiest to do with ``pluginmgr`` on a Viz
One server. It will help you to create the files you need. Before you start,
create a new folder and add a file named ``plugin`` to it, with these contents:

.. code-block:: yaml

    type: runnable
    package: myplugin
    depends: python-one
    methods: myplugin
    mode: filecopy
    title: My Plugin
    author: Vizrt
    version: 1.0
    source-scheme: ftp
    destination-scheme: ftp
    destination-conflicts: none
    killprocess: false
    partial: false
    partial-by-frame: false

You can now basically use ``pluginmgr make`` interactively until you get it right.

.. code-block:: bash

    mkdir myplugin
    cd myplugin
    vim plugin
    pluginmgr make

    # vdf: vdf model at ~/myplugin/etc/xfer-plugin-myplugin.vdf
    # required but missing at /opt/ardome/bin/pluginmgr line 847.

So, you need a VDF. This is for holding the settings of your plugin in a way
that is editable in Viz One's Administration console. You can use ``pluginmgr
vdf`` to create one:

.. code-block:: bash

    pluginmgr vdf plugin.user:Username:user …
        plugin.password:Password:user …
        > etc/xfer-plugin-myplugin.vdf

Now try ``pluginmgr make`` again:

.. code-block:: bash

    pluginmgr make

    # Could not find the specified bin/myplugin in source tree

So there is no plugin executable to run. For flow this will be a script, named
``bin/myplugin`` (where ``myplugin`` would be what you specified as ``method``
above) create a folder ``bin`` and put a file ``myplugin`` with this in it:

.. code-block:: bash

    #!/bin/bash

    /opt/python-one/bin/wrap_python -m flow …
        /opt/ardome/apps/myplugin/myplugin.ini -g

Note that the path might need to be adjusted later, but this is a decent
convention. Now try ``pluginmgr make`` again:

.. code-block:: bash

    pluginmgr make

    # INFO:
    # INFO: Edit files as necessary. Then run the following command to …
    #     build the apa-package:
    # INFO:
    # INFO:   $ apa dist xfer-plugin-myplugin/1.0
    # INFO:
    # INFO: To install:
    # INFO:   # scamp install -i [version] xfer-plugin-myplugin--1.0.apa
    # INFO:   # scamp apply
    # INFO:   $ ardemctl restart xfer
    # INFO:

Now ``pluginmgr`` is happy with the setup. Included here are also the
instructions on how to build an APA package out of this. It's not time for this
quite yet though, so just make a note of the command for later use. We should
create the actual app as well:

.. code-block:: bash

    mkdir -p apps/myplugin
    vim apps/myplugin/myplugin.py
    vim apps/myplugin/myplugin.ini

Good starting point for the ``myplugin.py`` file:

.. code-block:: python

    from flow.transfer import TransferPlugin
    from vizone import logging

    class MyPlugin(TransferPlugin):
        def start(self, plugin_data):
            self.use(plugin_data)

            self.update_progress(0)

            logging.info(u'Asset is %s', self.asset.title)
            logging.info(u'Source URL is %s', self.source)
            logging.info(u'Destination URL is %s', self.destination)

            self.update_progress(100)

And for the ``myplugin.ini`` file:

.. code-block:: ini

   [Flow]
   app name = myplugin
   class = myplugin.MyPlugin

   [Source]
   payload class = vizone.payload.transfer.PluginData

   [Viz One]
   use https = no


Now these files needs to be part of the APA package. To achieve this, edit the
file ``build/xfer-plugin-myplugin/FILES`` (the first line is new):

.. code-block:: text

    apps/myplugin/* -> apps/myplugin

    @ chmod 755
    bin/myplugin -> xferplugin/bin/myplugin
    @ nochmod

    @ nochmod
    @ chmod 644
    etc/xfer-plugin-myplugin.xml -> xferplugin/etc/xfer-plugin-myplugin.xml

    @ nochmod
    @ chmod 644
    etc/xfer-plugin-myplugin.vdf -> xferplugin/etc/xfer-plugin-myplugin.vdf

    @ nochmod

After changing this, **do not run ``pluginmgr make`` again**, as this will
overwrite the files in ``build/``. You can actually delete the ``plugin`` file
now and edit ``etc/xfer-plugin-myplugin.xml`` if you want to change any plugin
settings.


Creating and Installing a Package
---------------------------------

To build an APA package of your plugin, you can use the command given by
``pluginmgr make`` previously. Remember: don't run it again now!

.. code-block:: bash

    apa dist xfer-plugin-myplugin/1.0

.. note::

    The command ``apa`` might need to be called with explicit path, being
    ``/opt/scamp/bin/apa``.

This command should not give any output, but there should be an ``.apa`` file
in your working directory. Install this with scamp and restart the transfer
daemons:

.. code-block:: bash

    sudo /opt/scamp/bin/scamp install xfer-plugin-myplugin--1.0.apa
    sudo /opt/scamp/bin/scamp apply
    ardemctl restart xfer


Setting up a Rewrite Rule so the Plugin Gets Used
-------------------------------------------------

That the plugin exists does not mean it's automatically used. This example
shows how to set up an export storage and use it to export to it. First
create the export storage:

.. code-block:: bash

    storagemgr add stg plugin-export description="Plugin Export"
    storagemgr join export plugin-export
    mkdir /home/ardome/plugin-export
    sudo chown armedia:ardome /home/ardome/plugin-export
    sudo ln -s /home/ardome/plugin-export /ardome/media/exp/plugin-export
    storagemgr add mountpoint [INSERT SERVER HERE] plugin-export …
        /ardome/media/exp/plugin-export

To make every transfer to this new export destination use the plugin you must
create a rewrite rule. Run ``confmgr edit transfer.rewrite``, and add a new
one:

.. code-block:: yaml

    1:
      criteria:
        destination-storage:
          - plugin-export
      apply:
        destination-step-method: myplugin


Miscellaneous
=============

Various tools for making life easier.

Storing Data on the Server
--------------------------

.. autoclass:: flow.store.Store
   :members:


Parsing Data Fields with the MultiParser
----------------------------------------

.. autoclass:: flow.data.MultiParser
   :members:


Locking Based on a Key
----------------------

.. autoclass:: flow.lock.Locked
   :members:


Retrying on Conflict
--------------------

.. autofunction:: flow.operation.retry_on_conflict


