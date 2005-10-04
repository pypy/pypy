#! /usr/bin/env python
"""
Command-line interface for a dot file viewer -- either viewing normal .dot
files or connecting to a graph server like a browser.
"""

import autopath
import sys, py
from pypy.translator.tool.pygame import graphclient

from py.compat import optparse

usage = '''
        %s filename.dot
        %s hostname:port
        %s :port

In the first form, show the graph contained in a .dot file.
In the other forms, connect to a graph server like
goal/translate_pypy
''' % (sys.argv[0], sys.argv[0], sys.argv[0])

parser = optparse.OptionParser(usage=usage)
parser.add_option("--reload", action="store_true", dest="reload",
                  default=False, help="reload the dot file continously")


if __name__ == '__main__':
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.error("too many options")
        sys.exit(2)
    filename = args[0]
    if py.path.local(filename).check():
        graphclient.display_dot_file(filename,
                                     reload_repeatedly=options.reload)
    elif filename.count(':') != 1:
        print >> sys.stderr, 'No such file:', filename
        sys.exit(1)
    else:
        hostname, port = args[0].split(':')
        port = int(port)
        graphclient.display_remote_layout(hostname, port)
