==============
 Introduction
==============

Flow is a framework for writing tools, daemons and transfer plugins for `Viz
One <http://www.vizrt.com/products/viz_one/>`_, Vizrt's Media Asset Management
software. To communicate with Viz One, the Python SDK python-one is used.
Please contact Vizrt for your copy and more information.

The idea behind Flow is to make it simple to integrate with Viz One on an
enterprise level. The treats promoted by the framework are:

* Scalability (multi-threading and multi-server)
* Client statelessness
* Simplicity (one application does one thing)

To achieve this, all applications are limited to a certain structure:

.. code::

    Source -> Worker


The Source
==========

Let's start with the *Source*. The task of the Source is to gather information
in one way or another, do as little with it as possible, and hand it over to
the *Worker*. The Source runs in a single thread, which is the reason for
keeping the processing within it as simple as possible. Input to Sources can be
anything, but usually *Stomp*, *Files* or *Standard Input*.

Examples of built-in sources are:

* Asset Entry Listener :class:`flow.source.asset.AssetEntryListener`
  *Reacts on creations, updates and deletions of Asset Entries.*
* Unmanaged Files Listener :class:`flow.source.location.UnmanagedFilesListener`
  *Reacts on creations, updates and deletions of Unmanaged Files.*
* Generic Stomp Listener :class:`flow.source.stomp.GenericStompListener`
  *Subscribes to a manually given Stomp URL.*
* Interval :class:`flow.source.interval.Interval`
  *Spawns a worker every nth second.*
* STDIN :class:`flow.source.local.STDIN`
  *Reads from Standard Input and spawns a worker.*

You can also quite easily create your own Source class.


The Worker
==========

The Flow process will at start-up create a thread-pool that is used to run worker
threads. Workers are essentially classes with a ``start`` method and a ``SOURCE``
class specified. Optionally you can also have a ``configure`` method that will be
run once on start-up.

The ``start`` method will take an object as argument. This is the interface
between the *Source* and the *Worker*. The *Source* will call the ``start``
method with one object as argument as a new thread for each event it produces.
If there are no free workers, the event will be held until there are, and then
called. There is also a time out for execution time, meaning the waiting time
cannot be infinitely long.
