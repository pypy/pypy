#!/usr/bin/env python
""" Parse gcdumps. Use by saying PYPYLOG=gc-collect:log pypy <program>
and run it by:

gcanalyze.py logfile [--plot]
"""

import sys
from rpython.tool.logparser import parse_log

NO_BUCKETS = 8

def main(arg):
    log = parse_log(open(arg).readlines())
    all = []
    for entry in log:
        if entry[0].startswith('gc-collect'):
            start = entry[1]
            end = entry[2]
            all.append(float(end - start) / 1000000)
    avg = sum(all) / len(all)
    max_t = max(all)
    print "AVG:", "%.1fms" % avg, "MAX:", "%.1fms" % max_t
    buckets = [0] * (NO_BUCKETS + 1)
    for item in all:
        bucket = int(item / max_t * NO_BUCKETS)
        buckets[bucket] += 1
    l1 = ["%.1fms" % ((i + 1) * max_t / NO_BUCKETS) for i in range(NO_BUCKETS)]
    l2 = [str(i) for i in buckets[1:]]
    for i, elem in enumerate(l1):
        l2[i] += " " * (len(elem) - len(l2[i]))
    print " ".join(l1)
    print " ".join(l2)

if __name__ == '__main__':
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print __doc__
        sys.exit(1)
    plot = False
    if len(sys.argv) == 3:
        if sys.argv[1] == '--plot':
            plot = True
            arg = sys.argv[2]
        elif sys.argv[2] == '--plot':
            plot = True
            arg = sys.argv[1]
        else:
            print "Wrong command line options:", sys.argv
            sys.exit(1)
    else:
        arg = sys.argv[1]
    main(arg)
