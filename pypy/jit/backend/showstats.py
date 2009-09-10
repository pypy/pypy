#!/usr/bin/env python
import sys, py
from pypy.jit.metainterp.test.oparser import parse
from pypy.jit.metainterp.resoperation import rop
from pypy.rpython.lltypesystem import lltype, llmemory

class AllDict(dict):
    def __getitem__(self, item):
        return lltype.nullptr(llmemory.GCREF.TO)

alldict = AllDict()

def main(argv):
    lst = py.path.local(argv[0]).read().split("[")
    lst = ['[' + i for i in lst if i]
    for oplist in lst:
        loop = parse(oplist, namespace=alldict)
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
