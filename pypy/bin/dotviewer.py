#! /usr/bin/env python
"""
Command-line interface for a dot file viewer -- either viewing normal .dot
files or connecting to a graph server like a browser.
"""

import autopath
import sys, py
from pypy.translator.tool.pygame import graphclient


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print >> sys.stderr, 'Usage:  %s filename.dot' % (sys.argv[0],)
        print >> sys.stderr, '        %s hostname:port' % (sys.argv[0],)
        print >> sys.stderr, '        %s :port' % (sys.argv[0],)
        print >> sys.stderr
        print >> sys.stderr, ('In the first form, show the graph contained '
                              'in a .dot file.')
        print >> sys.stderr, ('In the other forms, connect to a graph server '
                              'like goal/translate_pypy.')
        sys.exit(2)
    filename = sys.argv[1]
    if py.path.local(filename).check():
        graphclient.display_dot_file(filename)
    elif filename.count(':') != 1:
        print >> sys.stderr, 'No such file:', filename
        sys.exit(1)
    else:
        hostname, port = sys.argv[1].split(':')
        port = int(port)
        graphclient.display_remote_layout(hostname, port)
