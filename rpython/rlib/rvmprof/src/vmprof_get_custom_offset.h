
#ifdef PYPY_JIT_CODEMAP
void *pypy_find_codemap_at_addr(long addr, long *start_addr);
long pypy_yield_codemap_at_addr(void *codemap_raw, long addr,
                                long *current_pos_addr);
long pypy_jit_stack_depth_at_loc(long loc);
#endif


#ifdef CPYTHON_GET_CUSTOM_OFFSET
static void *tramp_start, *tramp_end;
#endif

static long vmprof_write_header_for_jit_addr(void **result, long n,
                                             void *ip, int max_depth)
{
#ifdef PYPY_JIT_CODEMAP
    void *codemap;
    long current_pos = 0;
    intptr_t id;
    long start_addr = 0;
    intptr_t addr = (intptr_t)ip;
    int start, k;
    void *tmp;

    codemap = pypy_find_codemap_at_addr(addr, &start_addr);
    if (codemap == NULL)
        // not a jit code at all
        return n;

    // modify the last entry to point to start address and not the random one
    // in the middle
    result[n - 1] = (void*)start_addr;
    result[n] = (void*)2;
    n++;
    start = n;
    while (n < max_depth) {
        id = pypy_yield_codemap_at_addr(codemap, addr, &current_pos);
        if (id == -1)
            // finish
            break;
        if (id == 0)
            continue; // not main codemap
        result[n++] = (void *)id;
    }
    k = 0;
    while (k < (n - start) / 2) {
        tmp = result[start + k];
        result[start + k] = result[n - k - 1];
        result[n - k - 1] = tmp;
        k++;
    }
    if (n < max_depth) {
        result[n++] = (void*)3;
    }
#endif
    return n;
}
