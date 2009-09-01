#!/usr/bin/env python
""" Usage: loopviewer.py [loopnum] loopfile
"""

import py
import sys
from pypy.jit.metainterp.test.oparser import parse

def main(loopnum, loopfile):
    data = py.path.local(loopfile).read()
    loops = [i for i in data.split("[") if i]
    inp = "[" + loops[loopnum]
    loop = parse(inp)
    loop.show()

if __name__ == '__main__':
    if len(sys.argv) == 2:
        loopnum = -1
        loopfile = sys.argv[1]
    elif len(sys.argv) == 3:
        loopnum = int(sys.argv[1])
        loopfile = sys.argv[2]
    else:
        print __doc__
        sys.exit(1)
    main(loopnum, loopfile)
