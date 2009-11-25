#!/usr/bin/env python
""" Usage: gcdump.py gcdump typeids [outfile]
"""

from __future__ import division
import re
import sys

class GcDump(object):
    def __init__(self, count, size, links):
        self.count  = count
        self.size   = size
        self.links  = links

def read_gcdump(f):
    lines = f.readlines()
    r = [None] * len(lines)
    for i, line in enumerate(lines):
        count, size, rest = line.split(" ")
        r[i] = GcDump(int(count), int(size),
                      [int(j) for j in rest.split(",")])
    return r

def read_typeids(f):
    res = []
    for line in f.readlines():
        member, name = re.split("\s+", line, 1)
        assert member == "member%d" % len(res)
        res.append(name.strip("\n"))
    return res

def getname(name, _cache = {}):
    try:
        return _cache[name]
    except KeyError:
        no = len(_cache)
        _cache[name] = '(%d)' % len(_cache)
        return '(%d) %s' % (no, name)

def process(f, gcdump, typeids):
    f.write("events: number B\n\n")
    for tid, name in enumerate(typeids):
        if not tid % 100:
            sys.stderr.write("%d%%.." % (tid / len(typeids) * 100))
        f.write("fn=%s\n" % getname(name))
        f.write("0 %d %d\n" % (gcdump[tid].count, gcdump[tid].size))
        for subtid, no in enumerate(gcdump[tid].links):
            if no != 0:
                f.write("cfn=%s\n" % getname(typeids[subtid]))
                f.write("calls=0 %d\n" % no)
                f.write("0 %d %d\n" % (gcdump[subtid].count,
                                       gcdump[subtid].size))
        f.write("\n")
    sys.stderr.write("100%\n")

def main(gcdump_f, typeids_f, outfile):
    gcdump = read_gcdump(gcdump_f)
    gcdump_f.close()
    typeids = read_typeids(typeids_f)
    typeids_f.close()
    process(outfile, gcdump, typeids)

if __name__ == '__main__':
    if len(sys.argv) == 4:
        outfile = open(sys.argv[3], "w")
    elif len(sys.argv) == 3:
        outfile = sys.stdout
    else:
        print __doc__
        sys.exit(1)
    gcdump = open(sys.argv[1])
    typeids = open(sys.argv[2])
    main(gcdump, typeids, outfile)
    if len(sys.argv) == 4:
        outfile.close()
