#!/usr/bin/env python
"""
Parse and display the traces produced by pypy-c-jit when PYPYLOG is set.
"""

import autopath
import py
import sys
import optparse
from pprint import pprint
from pypy.tool import logparser
from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.metainterp.history import ConstInt
from pypy.rpython.lltypesystem import llmemory, lltype

def main(loopfile, options):
    print 'Loading file:'
    log = logparser.parse_log_file(loopfile)
    print
    loops = logparser.extract_category(log, "jit-log-opt-")
    if options.loopnum is None:
        input_loops = loops
    else:
        input_loops = [loops[options.loopnum]]
    loops = [parse(inp, no_namespace=True) for inp in input_loops]
    if not options.quiet:
        for loop in loops:
            loop.show()
    if options.summary:
        summary = {}
        for loop in loops:
            summary = loop.summary(summary)
        print 'Summary:'
        print_summary(summary)

def print_summary(summary):
    keys = sorted(summary)
    for key in keys:
        print '%4d' % summary[key], key

if __name__ == '__main__':
    parser = optparse.OptionParser(usage="%prog loopfile [options]")
    parser.add_option('-n', '--loopnum', dest='loopnum', default=-1, metavar='N', type=int,
                      help='show the loop number N [default: last]')
    parser.add_option('-a', '--all', dest='loopnum', action='store_const', const=None,
                      help='show all loops in the file')
    parser.add_option('-s', '--summary', dest='summary', action='store_true', default=False,
                      help='print a summary of the operations in the loop(s)')
    parser.add_option('-q', '--quiet', dest='quiet', action='store_true', default=False,
                      help='do not show the graphical representation of the loop')
    
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.print_help()
        sys.exit(2)

    main(args[0], options)
