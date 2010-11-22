# ../x86/jump.py
# XXX combine with ../x86/jump.py and move to llsupport
import sys
from pypy.tool.pairtype import extendabletype

def remap_frame_layout(assembler, src_locations, dst_locations, tmpreg):
    pending_dests = len(dst_locations)
    srccount = {}    # maps dst_locations to how many times the same
                     # location appears in src_locations
    for dst in dst_locations:
        srccount[dst.as_key()] = 0
    for i in range(len(dst_locations)):
        src = src_locations[i]
        if src.is_imm():
            continue
        key = src.as_key()
        if key in srccount:
            if key == dst_locations[i].as_key():
                srccount[key] = -sys.maxint     # ignore a move "x = x"
                pending_dests -= 1
            else:
                srccount[key] += 1

    while pending_dests > 0:
        progress = False
        for i in range(len(dst_locations)):
            dst = dst_locations[i]
            key = dst.as_key()
            if srccount[key] == 0:
                srccount[key] = -1       # means "it's done"
                pending_dests -= 1
                src = src_locations[i]
                if not src.is_imm():
                    key = src.as_key()
                    if key in srccount:
                        srccount[key] -= 1
                _move(assembler, src, dst, tmpreg)
                progress = True
        if not progress:
            # we are left with only pure disjoint cycles
            sources = {}     # maps dst_locations to src_locations
            for i in range(len(dst_locations)):
                src = src_locations[i]
                dst = dst_locations[i]
                sources[dst.as_key()] = src
            #
            for i in range(len(dst_locations)):
                dst = dst_locations[i]
                originalkey = dst.as_key()
                if srccount[originalkey] >= 0:
                    assembler.regalloc_push(dst)
                    while True:
                        key = dst.as_key()
                        assert srccount[key] == 1
                        # ^^^ because we are in a simple cycle
                        srccount[key] = -1
                        pending_dests -= 1
                        src = sources[key]
                        if src.as_key() == originalkey:
                            break
                        _move(assembler, src, dst, tmpreg)
                        dst = src
                    assembler.regalloc_pop(dst)
            assert pending_dests == 0

def _move(assembler, src, dst, tmpreg):
    if dst.is_stack() and src.is_stack():
        assembler.regalloc_mov(src, tmpreg)
        src = tmpreg
    assembler.regalloc_mov(src, dst)
