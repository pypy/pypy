#!/usr/bin/env python
import autopath
import sys, py
from pypy.jit.metainterp.test.oparser import parse, split_logs_into_loops
from pypy.jit.metainterp.resoperation import rop
from pypy.rpython.lltypesystem import lltype, llmemory

def main(argv):
    parts = split_logs_into_loops(py.path.local(argv[0]).read())
    for oplist in parts:
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
        print "Loop, length: %d, opcodes: %d, guards: %d" % (num_ops, num_dmp, num_guards)

if __name__ == '__main__':
    main(sys.argv[1:])
