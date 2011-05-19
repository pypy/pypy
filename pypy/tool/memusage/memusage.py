#! /usr/bin/env python
"""
Runs a subprocess, and measure its RSS (resident set size) every second.
At the end, print the maximum RSS measured, and some statistics.
Also writes 'memusage.log', reporting every second the RSS.
"""

import sys, os, re, time

args = sys.argv[1:]
if not args:
    print >> sys.stderr, __doc__
    sys.exit(2)
childpid = os.fork()
if childpid == 0:
    os.execvp(args[0], args)
    sys.exit(1)

r = re.compile("VmRSS:\s*(\d+)")

filename = '/proc/%d/status' % childpid
rss_max = 0
rss_sum = 0
rss_count = 0

f = open('memusage.log', 'w', 0)
while os.waitpid(childpid, os.WNOHANG)[0] == 0:
    g = open(filename)
    s = g.read()
    g.close()
    match = r.search(s)
    if not match:     # VmRSS is missing if the process just finished
        break
    rss = int(match.group(1))
    print >> f, rss
    if rss > rss_max: rss_max = rss
    rss_sum += rss
    rss_count += 1
    time.sleep(1)
f.close()

if rss_count > 0:
    print
    print 'Memory usage:'
    print '\tmaximum RSS: %10d kb' % rss_max
    print '\tmean RSS:    %10d kb' % (rss_sum / rss_count)
    print '\trun time:    %10d s' % rss_count
