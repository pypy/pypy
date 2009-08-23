

def remap_stack_layout(assembler, src_locations, dst_locations):
    for i in range(len(dst_locations)):
        src = src_locations[i]
        dst = dst_locations[i]
        if src is not dst:
            assembler.regalloc_load(src, dst)
