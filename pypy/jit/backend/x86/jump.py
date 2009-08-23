from pypy.jit.backend.x86.ri386 import MODRM


def remap_stack_layout(assembler, src_locations, dst_locations, free_regs=[]):
    for i in range(len(dst_locations)):
        src = src_locations[i]
        dst = dst_locations[i]
        if src is not dst:
            if isinstance(dst, MODRM):
                if isinstance(src, MODRM):
                    tmp = free_regs[0]
                    assembler.regalloc_load(src, tmp)
                    src = tmp
                assembler.regalloc_store(src, dst)
            else:
                assembler.regalloc_load(src, dst)
