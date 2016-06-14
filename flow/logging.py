##
# Copyright (C) 2015 Vizrt.  All rights reserved.
# This software is distributed under license and may not be copied,
# modified or distributed except if explicitly authorized by Vizrt.
# The right to use this software is limited by the license agreement.
# Further information is available at http://www.vizrt.com/
##

from __future__ import print_function
from threading import Lock, local
import pprint
import sys
from datetime import datetime
from lxml import etree
from requests.utils import CaseInsensitiveDict
from vizone.classutils import ensure_unicode_input, ensure_unicode

try:
    from pygments import highlight
    from pygments.lexers import get_lexer_by_name
    from pygments.formatters import TerminalFormatter
except ImportError:
    _have_pygment = False
else:
    _have_pygment = True

BOLD = "\033[1m"
DIM = "\033[2m"
UNDERLINE = "\033[4m"
BLINK = "\033[5m"
NORMAL = "\033[0;0m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
DEFAULT = "\033[39m"
WHITE = "\033[37m"
BACK_BLUE = "\033[44m"
BACK_DEFAULT = "\033[49m"

pp = pprint.PrettyPrinter(indent=2)


class TerminalLogger:
    def __init__(self):
        self.local = local()
        self.local.log_id = '*'
        self.lock = Lock()
        self.debug = False
        self.mute = False
        self.smute = []
        self.graphical = False
        self.color = True
        self.formal = False
        self.max_column_width = 100
        if _have_pygment:
            self.formatter = TerminalFormatter()
            self.lexer = get_lexer_by_name('xml')
            self.json_lexer = get_lexer_by_name('json')

    def set_log_id(self, log_id):
        self.local.log_id = log_id

    @property
    def log_id(self):
        if hasattr(self.local, 'log_id'):
            return self.local.log_id
        else:
            return '*'
    
    @ensure_unicode_input
    def log(self, desc, data=None, data_type=None, debug=False):
        with self.lock:
            try:
                desc = u'(%s) %s' % (str(self.log_id), desc)
                if self.mute or data_type in self.smute or (debug and not self.debug):
                    return
                if debug and data_type is None:
                    data_type = 'debug'
                ts = unicode(datetime.isoformat(datetime.now()) + ' ' if self.formal else '').encode('utf-8')
                if self.color and data_type != 'table':
                    if data_type == 'comment':
                        print(ts + BLUE + desc.strip().encode('utf-8') + NORMAL)
                    elif data_type == 'title':
                        print(ts + BOLD + BLUE + desc.strip().encode('utf-8') + NORMAL)
                    elif data_type == 'error':
                        print(ts + BOLD + RED + desc.encode('utf-8') + NORMAL, file=sys.stderr)
                    elif data_type == 'warn':
                        print(ts + BOLD + YELLOW + desc.encode('utf-8') + NORMAL, file=sys.stderr)
                    elif data_type == 'ok':
                        print(ts + BOLD + GREEN + desc.encode('utf-8') + NORMAL)
                    elif desc is not None:
                        print(ts + BOLD + desc.encode('utf-8') + NORMAL)
                elif data_type != 'table':
                    # Some trickery to ensure this is working for special chars in a demstart environment.
                    prefix = ts + (unicode(data_type) or u'info').upper()
                    postfix = ' ' + desc
                    all = unicode(prefix + postfix)
                    print(all.encode('utf-8'))
                if data is not None:
                    if _have_pygment and self.color and data_type == 'xml':
                        try:
                            data = etree.tostring(data)
                        except AttributeError:
                            pass
                        except TypeError:
                            pass
                        try:
                            data = data.decode('utf8')
                        except AttributeError:
                            data = unicode(data, 'utf8')
                        except UnicodeDecodeError:
                            pass
                        except UnicodeEncodeError:
                            pass
                        print(highlight(data, self.lexer, self.formatter))
                    elif _have_pygment and self.color and data_type == 'json':
                        print(highlight(data, self.json_lexer, self.formatter))
                    elif data_type in ('pp', 'error'):
                        if isinstance(data, CaseInsensitiveDict) or isinstance(data, dict):
                            if len(data) == 0:
                                print('{empty dict}', file=(sys.stderr if data_type == 'error' else sys.stdout))
                            else:
                                longest = max([len(k) for k in data.keys()])
                                for k, v in data.iteritems():
                                    print(((u'  %%-%is   %%s' % longest) % (k, v)).encode('utf-8'), file=(sys.stderr if data_type == 'error' else sys.stdout))
                                print('', file=(sys.stderr if data_type == 'error' else sys.stdout))
                        elif isinstance(data, unicode):
                            print(data.encode('utf-8'), file=(sys.stderr if data_type == 'error' else sys.stdout))
                        else:
                            pp.pprint(data)
                    elif data_type == 'table':
                        lengths = [len(x) for x in desc]
                        max_length = self.max_column_width
                        for row in data:
                            lengths = [min(max_length, max(lengths[n], len(unicode(x or '-')))) for n, x in enumerate(row)]
                        fs = '  '.join([('%%-%is' % l) for l in lengths])
                        if self.color:
                            print(BLUE + (fs % desc).encode('utf-8') + DEFAULT)
                        else:
                            print(fs % desc).encode('utf-8')
                        for row in data:
                            print(fs % tuple([(unicode(ensure_unicode(col)) or u'-')[:max_length].encode('utf-8') for col in row]))
                    else:
                        print(data.encode('utf-8'))
                sys.stdout.flush()
            except Exception as e:
                print("LOGGING ERROR: " + str(e), file=sys.stderr)

    def colorify(self, value, color=None):
        if color is None or not self.color:
            return value
        elif color == 'gray':
            return DIM + value + NORMAL
        elif color == 'green':
            return GREEN + BOLD + value + NORMAL
        elif color == 'blue':
            return BLUE + value + NORMAL
        elif color == 'red':
            return RED + value + NORMAL
        elif color == 'yellow':
            return YELLOW + value + NORMAL
        elif color == 'gray':
            return DIM + value + NORMAL
        elif color == 'gray':
            return DIM + value + NORMAL
        elif color == 'black':
            return BOLD + value + NORMAL
        else:
            print("Uknown color '%s'" % color)
            return value

    def close(self):
        pass


# For pretty printing in the terminal

def make_bold(s):
    return "%s%s%s" % (BOLD, s, NORMAL)


def make_dim(s):
    return "%s%s%s" % (DIM, s, NORMAL)


def make_underline(s):
    return "%s%s%s" % (UNDERLINE, s, NORMAL)


def make_BLINK(s):
    return "%s%s%s" % (BLINK, s, NORMAL)


def make_red(s):
    return "%s%s%s" % (RED, s, DEFAULT)


def make_green(s):
    return "%s%s%s" % (GREEN, s, DEFAULT)


def make_yellow(s):
    return "%s%s%s" % (YELLOW, s, DEFAULT)


def make_blue(s):
    return "%s%s%s" % (BLUE, s, DEFAULT)


def make_progress_bar(value, max_value, width):
    value = int(value)
    max_value = int(max_value)
    width = int(width)
    number = str(value) + ('%' if max_value == 100 else '')
    fmt = ' %-' + ('%i' % (width - 1)) + 's'
    s = fmt % number
    b = int(float(value) / float(max_value) * float(width))
    return BACK_BLUE + WHITE + s[:b] + BACK_DEFAULT + DEFAULT + s[b:]


def pretty(obj):
    pp.pprint(obj)
