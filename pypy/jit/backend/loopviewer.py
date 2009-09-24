#!/usr/bin/env python
""" Usage: loopviewer.py [loopnum] loopfile
"""

import py
import sys
from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.metainterp.history import ConstInt
from pypy.rpython.lltypesystem import llmemory, lltype

class AllDict(dict):
    def __getitem__(self, item):
        return lltype.nullptr(llmemory.GCREF.TO)

alldict = AllDict()

def main(loopnum, loopfile):
    data = py.path.local(loopfile).read()
    loops = [i for i in data.split("[") if i]
    inp = "[" + loops[loopnum]
    loop = parse(inp, namespace=alldict)
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
