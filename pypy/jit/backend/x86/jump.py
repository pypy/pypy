from pypy.jit.backend.x86.ri386 import *


def remap_stack_layout(assembler, src_locations, dst_locations, tmpreg):
    for i in range(len(dst_locations)):
        src = src_locations[i]
        dst = dst_locations[i]
        if src is not dst:
            if isinstance(dst, MODRM):
                if isinstance(src, MODRM):
                    assembler.regalloc_load(src, tmpreg)
                    src = tmpreg
                assembler.regalloc_store(src, dst)
            else:
                assembler.regalloc_load(src, dst)
