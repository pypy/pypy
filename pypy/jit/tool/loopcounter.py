#!/usr/bin/env python
"""
Parse and display the traces produced by pypy-c-jit when PYPYLOG is set.
"""

import autopath
import py
import sys
import optparse

def get_timestamp(line):
    import re
    match = re.match(r'\[([0-9a-f]*)\] .*', line)
    return int(match.group(1), 16)

def main(logfile, options):
    log = open(logfile)
    loops = 0
    bridges = 0
    time0 = None
    print 'timestamp,total,loops,bridges'
    for line in log:
        if time0 is None and line.startswith('['):
            time0 = get_timestamp(line)
        if '{jit-log-opt-' in line:
            time_now = get_timestamp(line)
            if '{jit-log-opt-loop' in line:
                loops += 1
            elif '{jit-log-opt-bridge' in line:
                bridges += 1
            else:
                assert False, 'unknown category %s' % line
            total = loops+bridges
            timestamp = time_now - time0
            print '%d,%d,%d,%d' % (timestamp, total, loops, bridges)

if __name__ == '__main__':
    parser = optparse.OptionParser(usage="%prog loopfile [options]")
    options, args = parser.parse_args()
    if len(args) != 1:
        parser.print_help()
        sys.exit(2)

    main(args[0], options)
