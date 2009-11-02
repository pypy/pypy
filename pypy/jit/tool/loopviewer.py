#!/usr/bin/env python
""" Usage: loopviewer.py [loopnum] loopfile
"""

import autopath
import py
import sys
from pypy.tool import logparser
from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.metainterp.history import ConstInt
from pypy.rpython.lltypesystem import llmemory, lltype

def main(loopnum, loopfile):
    log = logparser.parse_log_file(loopfile)
    loops = logparser.extract_category(log, "jit-log-opt-")
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
