#!/usr/bin/env python
from __future__ import division

import autopath
import sys, py
from pypy.tool import logparser
from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.metainterp.resoperation import rop
from pypy.rpython.lltypesystem import lltype, llmemory

def main(argv):
    log = logparser.parse_log_file(argv[0])
    parts = logparser.extract_category(log, "jit-log-opt-")
    for i, oplist in enumerate(parts):
        loop = parse(oplist, no_namespace=True)
        num_ops = 0
        num_dmp = 0
        num_guards = 0
        for op in loop.operations:
            if op.opnum == rop.DEBUG_MERGE_POINT:
                num_dmp += 1
            else:
                num_ops += 1
            if op.is_guard():
                num_guards += 1
        print "Loop #%d, length: %d, opcodes: %d, guards: %d, %f" % (i, num_ops, num_dmp, num_guards, num_ops/num_dmp)

if __name__ == '__main__':
    main(sys.argv[1:])
