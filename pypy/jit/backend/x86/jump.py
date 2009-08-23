import sys
from pypy.tool.pairtype import extendabletype
from pypy.jit.backend.x86.ri386 import *

class __extend__(REG):
    __metaclass__ = extendabletype
    def _getregkey(self):
        return ~self.op

class __extend__(MODRM):
    __metaclass__ = extendabletype
    def _getregkey(self):
        return self.position


def remap_stack_layout(assembler, src_locations, dst_locations, tmpreg):
    pending_dests = len(dst_locations)
    srccount = {}    # maps dst_locations to how many times the same
                     # location appears in src_locations
    for dst in dst_locations:
        srccount[dst._getregkey()] = 0
    for i in range(len(dst_locations)):
        src = src_locations[i]
        key = src._getregkey()
        if key in srccount:
            if key == dst_locations[i]._getregkey():
                srccount[key] = -sys.maxint     # ignore a move "x = x"
                pending_dests -= 1
            else:
                srccount[key] += 1

    while pending_dests > 0:
        for i in range(len(dst_locations)):
            dst = dst_locations[i]
            key = dst._getregkey()
            if srccount[key] == 0:
                srccount[key] = -1       # means "it's done"
                pending_dests -= 1
                src = src_locations[i]
                key = src._getregkey()
                if key in srccount:
                    srccount[key] -= 1
                _move(assembler, src, dst, tmpreg)


def _move(assembler, src, dst, tmpreg):
    if isinstance(dst, MODRM):
        if isinstance(src, MODRM):
            assembler.regalloc_load(src, tmpreg)
            src = tmpreg
        assembler.regalloc_store(src, dst)
    else:
        assembler.regalloc_load(src, dst)
