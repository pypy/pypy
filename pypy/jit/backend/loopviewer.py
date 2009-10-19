#!/usr/bin/env python
""" Usage: loopviewer.py [loopnum] loopfile
"""

import autopath
import py
import sys
from pypy.jit.metainterp.test.oparser import parse, split_logs_into_loops
from pypy.jit.metainterp.history import ConstInt
from pypy.rpython.lltypesystem import llmemory, lltype

def main(loopnum, loopfile):
    data = py.path.local(loopfile).read()
    loops = split_logs_into_loops(data)
    inp = loops[loopnum]
    loop = parse(inp, no_namespace=True)
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
