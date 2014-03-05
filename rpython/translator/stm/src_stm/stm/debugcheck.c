/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


#define DEBUG_SEEN_NO    '.'
#define DEBUG_SEEN_TAIL  '#'

static char *debug_seen;


static void debug_object(object_t *obj)
{
    if (obj == NULL)
        return;

    assert(((uintptr_t)obj & 7) == 0);
    uintptr_t rmindex = (((uintptr_t)obj) >> 4) - READMARKER_START;
    assert(rmindex < READMARKER_END - READMARKER_START);
    if (debug_seen[rmindex] != DEBUG_SEEN_NO) {
        assert(debug_seen[rmindex] == (uintptr_t)obj & 0x0f);
        return;
    }
    debug_seen[rmindex++] = (uintptr_t)obj & 0x0f;

    char *realobj0 = (char *)REAL_ADDRESS(stm_object_pages, obj);
    ssize_t size = stmcb_size_rounded_up(realobj0);
    assert(size >= 16);
    assert((size & 7) == 0);
    while (rmindex < (((uintptr_t)obj + size) >> 4) - READMARKER_START) {
        assert(debug_seen[rmindex] = DEBUG_SEEN_NO);
        debug_seen[rmindex++] = DEBUG_SEEN_TAIL;
    }

    bool small_uniform = false;

    uintptr_t first_page = ((uintptr_t)obj) / 4096;
    assert(first_page >= FIRST_OBJECT_PAGE);
    assert(first_page < NB_PAGES - 1);

    if (first_page < END_NURSERY_PAGE) {
        assert(_is_in_nursery(obj));

        /* object must be within the allocated part of the nursery */
        uintptr_t nursofs = ((uintptr_t)obj) - FIRST_NURSERY_PAGE * 4096UL;
        assert(nursofs < nursery_ctl.used);
    }
    else {
        assert(!_is_in_nursery(obj));

        if (realobj0 < uninitialized_page_start) {
            /* a large object */
            assert(realobj0 + size <= uninitialized_page_start);
        }
        else {
            /* a small object in a uniform page */
            small_uniform = true;
            assert(realobj0 >= uninitialized_page_stop);
            assert((uintptr_t)obj + size <= (NB_PAGES - 1) * 4096UL);
        }
    }

    long i;
    for (i = 0; i < NB_SEGMENTS; i++) {
        ...;
    }
    //...;
}

static void debug_check_roots(void)
{
    stm_thread_local_t *tl = stm_thread_locals;
    do {
        object_t **current = tl->shadowstack;
        object_t **base = tl->shadowstack_base;
        while (current-- != base) {
            debug_object(*current);
        }
        tl = tl->next;
    } while (tl != stm_thread_locals);
}

static void debug_check_segments(void)
{
    long i;
    for (i = 0; i < NB_SEGMENTS; i++) {
        struct stm_priv_segment_info_t *pseg = get_priv_segment(i);

        assert(pseg->pub.segment_num == i);
        assert(pseg->pub.segment_base == get_segment_base(i));

        if (pseg->pub.nursery_current == NULL) {
            assert(pseg->real_nursery_section_end == NULL);
        }
        else {
            assert(pseg->real_nursery_section_end != NULL);
            assert((pseg->real_nursery_section_end & NURSERY_LINE) == 0);
            assert((uintptr_t)(pseg->real_nursery_section_end -
                               (uintptr_t)pseg->pub.nursery_current)
                   <= NURSERY_SECTION_SIZE);
        }
        assert(pseg->pub.v_nursery_section_end ==
                   pseg->real_nursery_section_end ||
               pseg->pub.v_nursery_section_end == NSE_SIGNAL ||
               pseg->pub.v_nursery_section_end == NSE_SIGNAL_DONE);

        assert((pseg->pub.running_thread != NULL) ==
               (pseg->transaction_state != TS_NONE));

        if (pseg->transaction_state != TS_NONE) {
            assert(1 <= pseg->min_read_version_outside_nursery);
            assert(pseg->min_read_version_outside_nursery <=
                       pseg->pub.transaction_read_version);
        }
    }
}

void stm_debug_check_objects(void)
{
    /* Not thread-safe!

       Check the consistency of every object reachable from the roots,
       the pages, the global allocation variables, the various markers,
       and so on.

       Reading this is probably a good way to learn about all the
       implicit invariants.
    */

    debug_seen = malloc(READMARKER_END - READMARKER_START);
    memset(debug_seen, DEBUG_SEEN_NO, READMARKER_END - READMARKER_START);

    /* Check the segment state */
    debug_check_segments();

    /* Follow objects from the roots */
    debug_check_roots();



    free(debug_seen);
    debug_seen = NULL;
}
