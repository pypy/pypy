from pypy.jit.backend.x86.ri386 import MODRM, eax


def remap_stack_layout(assembler, src_locations, dst_locations, free_regs=[]):
    pending_pops = []
    for i in range(len(dst_locations)):
        src = src_locations[i]
        dst = dst_locations[i]
        if src is not dst:
            if isinstance(dst, MODRM):
                if isinstance(src, MODRM):
                    if free_regs:
                        tmp = free_regs[0]
                    else:
                        assembler.regalloc_push(eax)
                        pending_pops.append(eax)
                        tmp = eax
                    assembler.regalloc_load(src, tmp)
                    src = tmp
                assembler.regalloc_store(src, dst)
            else:
                assembler.regalloc_load(src, dst)
    for reg in pending_pops:
        assembler.regalloc_pop(reg)
