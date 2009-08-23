from pypy.jit.backend.x86.ri386 import *


def remap_stack_layout(assembler, src_locations, dst_locations, free_regs=[]):
    pushed_eax = False
    for i in range(len(dst_locations)):
        src = src_locations[i]
        dst = dst_locations[i]
        if src is not dst:
            if pushed_eax and src is eax:
                assembler.regalloc_load(mem(esp, 0), src)
            if isinstance(dst, MODRM):
                if isinstance(src, MODRM):
                    if free_regs:
                        tmp = free_regs[0]
                    else:
                        assembler.regalloc_push(eax)
                        pushed_eax = True
                        tmp = eax
                    assembler.regalloc_load(src, tmp)
                    src = tmp
                assembler.regalloc_store(src, dst)
            else:
                assembler.regalloc_load(src, dst)
    if pushed_eax:
        assembler.regalloc_pop(eax)
