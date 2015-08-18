
#ifdef PYPY_JIT_CODEMAP
void *pypy_find_codemap_at_addr(long addr, long *start_addr);
long pypy_yield_codemap_at_addr(void *codemap_raw, long addr,
                                long *current_pos_addr);
long pypy_jit_stack_depth_at_loc(long loc);
#endif


#ifdef CPYTHON_GET_CUSTOM_OFFSET
static void *tramp_start, *tramp_end;
#endif


static ptrdiff_t vmprof_unw_get_custom_offset(void* ip, void *cp) {

#if defined(PYPY_JIT_CODEMAP)

    intptr_t ip_l = (intptr_t)ip;
    return pypy_jit_stack_depth_at_loc(ip_l);

#elif defined(CPYTHON_GET_CUSTOM_OFFSET)

    if (ip >= tramp_start && ip <= tramp_end) {
        // XXX the return value is wrong for all the places before push and
        //     after pop, fix
        void *bp;
        void *sp;

        /* This is a stage2 trampoline created by hotpatch:

               push   %rbx
               push   %rbp
               mov    %rsp,%rbp
               and    $0xfffffffffffffff0,%rsp   // make sure the stack is aligned
               movabs $0x7ffff687bb10,%rbx
               callq  *%rbx
               leaveq 
               pop    %rbx
               retq   

           the stack layout is like this:

               +-----------+                      high addresses
               | ret addr  |
               +-----------+
               | saved rbx |   start of the function frame
               +-----------+
               | saved rbp |
               +-----------+
               | ........  |   <-- rbp
               +-----------+                      low addresses

           So, the trampoline frame starts at rbp+16, and the return address,
           is at rbp+24.  The vmprof API requires us to return the offset of
           the frame relative to sp, hence we have this weird computation.

           XXX (antocuni): I think we could change the API to return directly
           the frame address instead of the offset; however, this require a
           change in the PyPy code too
        */

        unw_get_reg (cp, UNW_REG_SP, (unw_word_t*)&sp);
        unw_get_reg (cp, UNW_X86_64_RBP, (unw_word_t*)&bp);
        return bp+16+8-sp;
    }
    return -1;

#else

    return -1;

#endif
}

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
