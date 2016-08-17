
void *pypy_find_codemap_at_addr(long addr, long *start_addr);
long pypy_yield_codemap_at_addr(void *codemap_raw, long addr,
                                long *current_pos_addr);


static long vmprof_write_header_for_jit_addr(intptr_t *result, long n,
                                             intptr_t ip, int max_depth)
{
#ifdef PYPY_JIT_CODEMAP
    void *codemap;
    long current_pos = 0;
    intptr_t ident;
    long start_addr = 0;
    intptr_t addr = (intptr_t)ip;
    int start, k;
    intptr_t tmp;

    codemap = pypy_find_codemap_at_addr(addr, &start_addr);
    if (codemap == NULL || n >= max_depth - 2)
        // not a jit code at all or almost max depth
        return n;

    // modify the last entry to point to start address and not the random one
    // in the middle
    result[n++] = VMPROF_ASSEMBLER_TAG;
    result[n++] = start_addr;
    start = n;
    while (n < max_depth) {
        ident = pypy_yield_codemap_at_addr(codemap, addr, &current_pos);
        if (ident == -1)
            // finish
            break;
        if (ident == 0)
            continue; // not main codemap
        result[n++] = VMPROF_JITTED_TAG;
        result[n++] = ident;
    }
    k = 1;

    while (k < (n - start) / 2) {
        tmp = result[start + k];
        result[start + k] = result[n - k];
        result[n - k] = tmp;
        k += 2;
    }
#endif
    return n;
}
