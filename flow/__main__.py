#!/usr/bin/env wrap_python

import sys
import os
import time
import ConfigParser
from argparse import ArgumentParser

from vizone import logging
from vizone.tool import Tool
from vizone.client import init
from vizone.net.message_queue import ConnectionManager
from vizone.classutils import to_class

from .base import Once, Iterable, EventBased
from .multi import Pool, LogId
from .needs import NeedsStomp, NeedsClient, NeedsStore, NeedsConfig, NeedsCleanUp
from .store import Store


def get_stomp(username, password, app_name, heartbeat_interval, heartbeat_timeout, heartbeats):
    if hasattr(get_stomp, 'cached'):
        return get_stomp.cached

    get_stomp.cached = ConnectionManager(
        "flow_%s" % app_name,
        username=username,
        password=password,
        heartbeat_interval=heartbeat_interval
            if heartbeats else None,
        heartbeat_timeout=heartbeat_timeout
            if heartbeats else None,
    )

    logging.log("Stomp settings", {
        '(from Flow section) app name': app_name,
        'heartbeats': heartbeats,
        'heartbeat interval': heartbeat_interval,
        'heartbeat timeout': heartbeat_timeout,
    }, 'pp')

    return get_stomp.cached


def equip(app_name, username, password, args, client, config, klass, obj):
    if issubclass(klass, NeedsStomp):
        stomp = get_stomp(username, password, app_name,
                config.getfloat('Stomp', 'heartbeat interval'),
                config.getfloat('Stomp', 'heartbeat timeout'),
                config.getboolean('Stomp', 'heartbeats'))
        obj.set_stomp(stomp)
    if issubclass(klass, NeedsClient):
        obj.set_client(client)
    if issubclass(klass, NeedsStore):
        obj.set_store(Store("flow_" + app_name, client))
    if issubclass(klass, NeedsConfig):
        obj.configure(config)


if __name__ == '__main__':
    argparser = ArgumentParser(usage='python -m flow ini-file')

    argparser.add_argument(
        'profile',
        help='path to profile ini file')
    argparser.add_argument(
        '--instance-name', '-n',
        help='unique instance name')
    argparser.add_argument(
        '--workers', '-w', type=int, default=0,
        help='number of workers')
    argparser.add_argument(
        '--man', action="store_true",
        help="show man page for the loaded profile")
    argparser.add_argument(
        '--debug', '-g', action="store_true",
        help="log in debug level")

    args = argparser.parse_args()

    config = ConfigParser.ConfigParser()
    config.optionxform = str  # do not lowercase keys

    # Default config
    config.add_section('Flow')
    config.set('Flow', 'app name', 'default')
    config.set('Flow', 'class', 'path.to.flow.class')
    config.set('Flow', 'workers', '1')

    config.add_section('Source')

    config.add_section('Logging')
    config.set('Logging', 'level', 'info')
    config.set('Logging', 'color', 'yes')
    config.set('Logging', 'logger', 'flow')
    config.set('Logging', 'formal', 'no')
    config.set('Logging', 'file name', "/tmp/log.txt")

    config.add_section('Viz One')
    config.set('Viz One', 'enabled', 'yes')
    config.set('Viz One', 'hostname', 'localhost')
    config.set('Viz One', 'username', 'user')
    config.set('Viz One', 'password', 'user')
    config.set('Viz One', 'use https', 'yes')
    config.set('Viz One', 'check certificates', 'yes')
    config.set('Viz One', 'pem file', '')
    config.set('Viz One', 'time out', '60')

    config.add_section('Stomp')
    config.set('Stomp', 'heartbeats', 'yes')
    config.set('Stomp', 'heartbeat interval', '5')
    config.set('Stomp', 'heartbeat timeout', '10')

    # Read profile (ini file)
    config.read(args.profile)

    # Stomp object placeholder
    stomp = None

    # Set up environment
    working_dir = os.path.dirname(os.path.abspath(args.profile))
    os.chdir(working_dir)
    sys.path.append(working_dir)

    # Load application
    Flow = to_class(config.get('Flow', 'class'))
    app_name = args.instance_name or config.get('Flow', 'app name')

    # Show help
    if args.man:
        help(Flow)
        sys.exit(0)

    # Set up multi-threading
    workers = args.workers or config.getint('Flow', 'workers')
    workers = max(workers, 1)

    # Set up Logging
    logging_debug = config.get('Logging', 'level') == 'debug'
    logging_color = config.getboolean('Logging', 'color')
    logging_logger = config.get('Logging', 'logger')
    logging_formal = config.getboolean('Logging', 'formal')
    logging_file = config.get('Logging', 'file name')

    if logging_logger == 'flow':
        from .logging import TerminalLogger
        logger = TerminalLogger()
        logger.color = logging_color
        if logging_formal:
            logger.color = False
            logger.formal = True
        logging.set_logger(logger)

    elif logging_logger == 'terminal':
        from vizone.logging.terminal import TerminalLogger
        logger = TerminalLogger()
        logger.color = logging_color
        if logging_formal:
            logger.color = False
            logger.formal = True
        logging.set_logger(logger)

    elif args.logger == 'html':
        from vizone.logging.html import HtmlLogger
        logger = HtmlLogger()
        logging.set_logger(logger)

    elif args.logger == 'file':
        from vizone.logging.file import FileLogger
        logger = FileLogger(logging_file or os.path.join('/tmp', app_name + '.log'))
        logging.set_logger(logger)

    logging.get_default_logger().debug = args.debug or logging_debug

    logging.log("Flow settings", {
        'app name': app_name,
        'class': Flow.__name__,
        'workers': workers,
        '(from ini path) working directory': working_dir,
        '(from main class SOURCE) source class': Flow.SOURCE.__name__,
    }, 'pp')

    # Set up Viz One Client Instance
    viz_one_enabled = config.getboolean('Viz One', 'enabled')
    viz_one_hostname = config.get('Viz One', 'hostname')
    viz_one_username = config.get('Viz One', 'username')
    viz_one_password = config.get('Viz One', 'password')
    viz_one_use_https = config.getboolean('Viz One', 'use https')
    viz_one_check_certificates = config.getboolean('Viz One', 'check certificates')
    viz_one_pem_file = os.path.expanduser(os.path.expandvars(config.get('Viz One', 'pem file'))) or None
    viz_one_time_out = config.getfloat('Viz One', 'time out')

    logging.log("Viz One Settings", {
        'enabled': viz_one_enabled,
        'hostname': viz_one_hostname,
        'username': viz_one_username,
        'password': '********' if viz_one_password else None,
        'use https': viz_one_use_https,
        'check certificates': viz_one_check_certificates,
        'pem file': viz_one_pem_file,
        'time out': viz_one_time_out,
    }, 'pp')

    if viz_one_enabled:
        client = init(
            hostname=viz_one_hostname,
            user=viz_one_username,
            password=viz_one_password,
            secure=viz_one_use_https,
            verify=viz_one_pem_file or viz_one_check_certificates,
            timeout=viz_one_time_out,
        )
    else:
        client = None

    source = Flow.SOURCE(**{k.replace(' ', '_'): v for k, v in config.items('Source')})
    equip(app_name, viz_one_username, viz_one_password, args, client, config, Flow.SOURCE, source)

    flow = Flow(instance_name=app_name)
    equip(app_name, viz_one_username, viz_one_password, args, client, config, Flow, flow)

    # Run source.run once, which should call the workers' start method once or
    # more. No parallelisation is done here
    if issubclass(Flow.SOURCE, Once):
        obj = source.run()
        flow.start(obj)

    # Run source.start multiple times as long as there are free workers in the
    # pool. Stop when source.next() raises StopIteration.
    elif issubclass(Flow.SOURCE, Iterable):
        with Pool(workers=workers, join=True) as pool:
            log_id = LogId()

            for obj in source:
                current_log_id = log_id.next()
                pool.spawn(flow.start, obj, logger=logger, log_id=current_log_id)
                logging.info(
                    "Spawned worker.",
                    current_log_id
                )

            logging.info("Source is out of data.")

    # Run source.start once and go to an idle loop. Source is typically an
    # event listener of some kind and will call the callback upon
    # external triggers.
    elif issubclass(Flow.SOURCE, EventBased):
        with Pool(workers=workers, join=True) as pool:
            log_id = LogId()

            def work(obj):
                current_log_id = log_id.next()
                pool.spawn(flow.start, obj, logger=logger, log_id=current_log_id)
                logging.info("Spawned (%s)." % (str(current_log_id)))

            source.callback = work
            source.run()
            while True:
                time.sleep(1)

    else:
        raise ValueError(
            "The Source class must inherit one of Once, Iterable or EventBased"
        )

    # Clean Up
    if issubclass(Flow, NeedsCleanUp):
        logging.info("Cleaning up flow...")
        obj.clean_up()

    elif issubclass(Flow.SOURCE, NeedsCleanUp):
        logging.info("Cleaning up source...")
        source.clean_up()

    logging.info("End of program.")
