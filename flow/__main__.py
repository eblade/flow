#!/usr/bin/env wrap_python

import sys
import os
import ConfigParser

from vizone import logging
from vizone.tool import Tool
from vizone.net.message_queue import ConnectionManager
from vizone.classutils import to_class

from .base import Once, Iterable, EventBased
from .multi import Pool
from .logging import LogId
from .needs import NeedsStomp, NeedsClient, NeedsStore, NeedsConfig
from .store import Store


# Initialize as "tool" with standard command line args
tool = Tool('flow', skip_api=False)
tool.add_argument('profile',
                  help='path to profile ini file')
tool.add_argument('--instance-name', '-n', default="default",
                  help='unique instance name')
tool.add_argument('--workers', '-w', type=int, default=1,
                  help='number of workers')
tool.add_argument('--man', action="store_true",
                  help="Show man page for the loaded daemon")

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


def equip(tool, args, client, config, klass, obj):
    if issubclass(klass, NeedsStomp):
        stomp = get_stomp(tool, args)
        obj.set_stomp(stomp)
    if issubclass(klass, NeedsClient):
        obj.set_client(client)
    if issubclass(klass, NeedsStore):
        obj.set_store(Store("flow_" + args.instance_name, client))
    if issubclass(klass, NeedsConfig):
        obj.configure(config)


if __name__ == '__main__':
    args, client = tool.init()

    config = ConfigParser.ConfigParser()
    config.read(args.profile)

    stomp = None

    working_dir = os.path.dirname(os.path.abspath(args.profile))
    os.chdir(working_dir)
    sys.path.append(working_dir)
    Flow = to_class(config.get('Flow', 'class'))

    if args.man:
        help(Flow)
        sys.exit(0)

    source = Flow.SOURCE(**{k.replace(' ', '_'): v for k, v in config.items('Source')})
    equip(tool, args, client, config, Flow.SOURCE, source)

    flow = Flow(instance_name=args.instance_name)
    equip(tool, args, client, config, Flow, flow)

    tool.message_queue = stomp

    # Run source.run once, which should call the workers' start method once or
    # more. No parallelisation is done here
    if issubclass(Flow.SOURCE, Once):
        obj, info = source.run()
        flow.start(obj, info)

    # Run source.run multiple times as long as there are free workers in the
    # pool. Stop when source.next() raises StopIteration.
    elif issubclass(Flow.SOURCE, Iterable):
        with Pool(workers=args.workers, join=True) as pool:
            log_id = LogId()

            for obj, info in source:
                current_log_id = log_id.next()
                pool.spawn(flow.run, obj, info=info, log_id=current_log_id)
                logging.debug(
                    "(%i) Spawned worker.",
                    current_log_id
                )

            logging.info("Source is out of data.")


    # Run source.run once and go to an idle loop. Source is typically an
    # event listener of some kind and will call the callback upon 
    # external triggers.
    else:
        with Pool(workers=args.workers, join=True) as pool:
            log_id = LogId()

            def work(obj, info):
                current_log_id = log_id.next()
                pool.spawn(flow.start, obj, info=info, log_id=current_log_id)
                logging.info("(%i) Spawned.", current_log_id)

            source.callback = work
            source.run()
            tool.run()
