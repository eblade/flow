#!/usr/bin/env wrap_python

from gevent import monkey; monkey.patch_all() 
from gevent.pool import Pool

import ConfigParser

from vizone import logging
from vizone.tool import Tool
from vizone.net.message_queue import ConnectionManager
from vizone.classutils import to_class

from .store import Store
from .util import LogId
from . import NeedsStomp, NeedsClient, NeedsStore


# Initialize as "tool" with standard command line args
tool = Tool('flow', skip_api=False)
tool.add_argument('profile',
                  help='path to profile ini file')
tool.add_argument('--instance-name', '-n', default="default",
                  help='unique instance name')
tool.add_argument('--workers', '-w', type=int, default=1,
                  help='number of workers')

def get_stomp(tool, args):
    if hasattr(get_stomp, 'cached'):
        return get_stomp.cached

    get_stomp.cached = ConnectionManager(
        "flow_%s" % args.instance_name,
        username=tool.user,
        password=tool.password,
        heartbeat_interval=args.stomp_heartbeat_interval
            if not args.stomp_disable_heartbeats else None,
        heartbeat_timeout=args.stomp_heartbeat_timeout
            if not args.stomp_disable_heartbeats else None,
    )

    return get_stomp.cached


def equip(tool, args, client, klass, obj):
    if issubclass(klass, NeedsStomp):
        stomp = get_stomp(tool, args)
        obj.set_stomp(stomp)
    if issubclass(klass, NeedsClient):
        obj.set_client(client)
    if issubclass(klass, NeedsStore):
        obj.set_store(Store("flow_" + args.instance_name, client))


if __name__ == '__main__':
    args, client = tool.init()

    config = ConfigParser.ConfigParser()
    config.read(args.profile)

    stomp = None

    Flow = to_class(config.get('Flow', 'class'))

    source = Flow.SOURCE(**{k.replace(' ', '_'): v for k, v in config.items('Source')})
    equip(tool, args, client, Flow.SOURCE, source)

    flow = Flow(instance_name=args.instance_name)
    equip(tool, args, client, Flow, flow)

    tool.message_queue = stomp

    pool = Pool(args.workers)
    log_id = LogId()

    def work(obj, info):
        pool.spawn(flow.start, obj, info=info, log_id=log_id.next())

    source.callback = work
    source.run()
    tool.run()
