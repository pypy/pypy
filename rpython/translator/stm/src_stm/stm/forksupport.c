/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


/* XXX this is currently not doing copy-on-write, but simply forces a
   copy of all pages as soon as fork() is called. */


static char *fork_big_copy = NULL;
static int fork_big_copy_fd;
static stm_thread_local_t *fork_this_tl;
static bool fork_was_in_transaction;

static bool page_is_null(char *p)
{
    long *q = (long *)p;
    long i;
    for (i = 0; i < 4096 / sizeof(long); i++)
        if (q[i] != 0)
            return false;
    return true;
}


static void forksupport_prepare(void)
{
    if (stm_object_pages == NULL)
        return;

    /* So far we attempt to check this by walking all stm_thread_local_t,
       marking the one from the current thread, and verifying that it's not
       running a transaction.  This assumes that the stm_thread_local_t is just
       a __thread variable, so never changes threads.
    */
    s_mutex_lock();

    dprintf(("forksupport_prepare\n"));
    fprintf(stderr, "[forking: for now, this operation can take some time]\n");

    stm_thread_local_t *this_tl = NULL;
    stm_thread_local_t *tl = stm_all_thread_locals;
    do {
        if (pthread_equal(*_get_cpth(tl), pthread_self())) {
            if (this_tl != NULL)
                stm_fatalerror("fork(): found several stm_thread_local_t"
                               " from the same thread");
            this_tl = tl;
        }
        tl = tl->next;
    } while (tl != stm_all_thread_locals);

    if (this_tl == NULL)
        stm_fatalerror("fork(): found no stm_thread_local_t from this thread");
    s_mutex_unlock();

    bool was_in_transaction = _stm_in_transaction(this_tl);
    if (was_in_transaction) {
        stm_become_inevitable(this_tl, "fork");
        /* Note that the line above can still fail and abort, which should
           be fine */
    }
    else {
        stm_start_inevitable_transaction(this_tl);
    }

    s_mutex_lock();
    synchronize_all_threads(STOP_OTHERS_UNTIL_MUTEX_UNLOCK);

    /* Make a new mmap at some other address, but of the same size as
       the standard mmap at stm_object_pages
    */
    int big_copy_fd;
    char *big_copy = setup_mmap("stmgc's fork support", &big_copy_fd);

    /* Copy each of the segment infos into the new mmap, nurseries,
       and associated read markers
     */
    long i;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        char *src, *dst;
        struct stm_priv_segment_info_s *psrc = get_priv_segment(i);
        dst = big_copy + (((char *)psrc) - stm_object_pages);
        *(struct stm_priv_segment_info_s *)dst = *psrc;

        src = get_segment_base(i) + FIRST_READMARKER_PAGE * 4096UL;
        dst = big_copy + (src - stm_object_pages);
        long j;
        for (j = 0; j < END_NURSERY_PAGE - FIRST_READMARKER_PAGE; j++) {
            if (!page_is_null(src))
                pagecopy(dst, src);
            src += 4096;
            dst += 4096;
        }
    }

    /* Copy all the data from the two ranges of objects (large, small)
       into the new mmap
    */
    uintptr_t pagenum, endpagenum;
    pagenum = END_NURSERY_PAGE;   /* starts after the nursery */
    endpagenum = (uninitialized_page_start - stm_object_pages) / 4096UL;
    if (endpagenum < NB_PAGES)
        endpagenum++;   /* the next page too, because it might contain
                           data from largemalloc */

    while (1) {
        if (UNLIKELY(pagenum == endpagenum)) {
            /* we reach this point usually twice, because there are
               more pages after 'uninitialized_page_stop' */
            if (endpagenum == NB_PAGES)
                break;   /* done */
            pagenum = (uninitialized_page_stop - stm_object_pages) / 4096UL;
            pagenum--;   /* the prev page too, because it does contain
                            data from largemalloc */
            endpagenum = NB_PAGES;
        }

        char *src = stm_object_pages + pagenum * 4096UL;
        char *dst = big_copy + pagenum * 4096UL;
        pagecopy(dst, src);

        struct page_shared_s ps = pages_privatized[pagenum - PAGE_FLAG_START];
        if (ps.by_segment != 0) {
            long j;
            for (j = 0; j < NB_SEGMENTS; j++) {
                src += NB_PAGES * 4096UL;
                dst += NB_PAGES * 4096UL;
                if (ps.by_segment & (1 << j)) {
                    pagecopy(dst, src);
                }
            }
        }
        pagenum++;
    }

    assert(fork_big_copy == NULL);
    fork_big_copy = big_copy;
    fork_big_copy_fd = big_copy_fd;
    fork_this_tl = this_tl;
    fork_was_in_transaction = was_in_transaction;

    assert(_has_mutex());
    dprintf(("forksupport_prepare: from %p %p\n", fork_this_tl,
             fork_this_tl->creating_pthread[0]));
}

static void forksupport_parent(void)
{
    if (stm_object_pages == NULL)
        return;

    dprintf(("forksupport_parent: continuing to run %p %p\n", fork_this_tl,
             fork_this_tl->creating_pthread[0]));
    assert(_has_mutex());
    assert(_is_tl_registered(fork_this_tl));

    /* In the parent, after fork(), we can simply forget about the big copy
       that we made for the child.
    */
    assert(fork_big_copy != NULL);
    munmap(fork_big_copy, TOTAL_MEMORY);
    fork_big_copy = NULL;
    close_fd_mmap(fork_big_copy_fd);
    bool was_in_transaction = fork_was_in_transaction;

    s_mutex_unlock();

    if (!was_in_transaction) {
        stm_commit_transaction();
    }

    dprintf(("forksupport_parent: continuing to run\n"));
}

static void fork_abort_thread(long i)
{
    struct stm_priv_segment_info_s *pr = get_priv_segment(i);
    stm_thread_local_t *tl = pr->pub.running_thread;
    dprintf(("forksupport_child: abort in seg%ld\n", i));
    assert(tl->associated_segment_num == i);
    assert(pr->transaction_state == TS_REGULAR);
    set_gs_register(get_segment_base(i));
    assert(STM_SEGMENT->segment_num == i);

    s_mutex_lock();
#ifndef NDEBUG
    pr->running_pthread = pthread_self();
#endif
    strcpy(pr->marker_self, "fork");
    tl->shadowstack = NULL;
    pr->shadowstack_at_start_of_transaction = NULL;
    stm_rewind_jmp_forget(tl);
    abort_with_mutex_no_longjmp();
    s_mutex_unlock();
}

static void forksupport_child(void)
{
    if (stm_object_pages == NULL)
        return;

    /* this new process contains no other thread, so we can
       just release these locks early */
    s_mutex_unlock();

    /* Move the copy of the mmap over the old one, overwriting it
       and thus freeing the old mapping in this process
    */
    assert(fork_big_copy != NULL);
    assert(stm_object_pages != NULL);
    void *res = mremap(fork_big_copy, TOTAL_MEMORY, TOTAL_MEMORY,
                       MREMAP_MAYMOVE | MREMAP_FIXED,
                       stm_object_pages);
    if (res != stm_object_pages)
        stm_fatalerror("after fork: mremap failed: %m");
    fork_big_copy = NULL;
    close_fd_mmap(stm_object_pages_fd);
    stm_object_pages_fd = fork_big_copy_fd;

    /* Unregister all other stm_thread_local_t, mostly as a way to free
       the memory used by the shadowstacks
     */
    while (stm_all_thread_locals->next != stm_all_thread_locals) {
        if (stm_all_thread_locals == fork_this_tl)
            stm_unregister_thread_local(stm_all_thread_locals->next);
        else
            stm_unregister_thread_local(stm_all_thread_locals);
    }
    assert(stm_all_thread_locals == fork_this_tl);

    /* Restore the base setting of PROT_NONE pages.
     */
    setup_protection_settings();

    /* Make all pages shared again.
     */
    uintptr_t pagenum, endpagenum;
    pagenum = END_NURSERY_PAGE;   /* starts after the nursery */
    endpagenum = (uninitialized_page_start - stm_object_pages) / 4096UL;

    while (1) {
        if (UNLIKELY(pagenum == endpagenum)) {
            /* we reach this point usually twice, because there are
               more pages after 'uninitialized_page_stop' */
            if (endpagenum == NB_PAGES)
                break;   /* done */
            pagenum = (uninitialized_page_stop - stm_object_pages) / 4096UL;
            endpagenum = NB_PAGES;
            if (endpagenum == NB_PAGES)
                break;   /* done */
        }

        struct page_shared_s ps = pages_privatized[pagenum - PAGE_FLAG_START];
        long j;
        for (j = 0; j < NB_SEGMENTS; j++) {
            if (!(ps.by_segment & (1 << j))) {
                _page_do_reshare(j + 1, pagenum);
            }
        }
        pagenum++;
    }

    /* Force the interruption of other running segments
     */
    long i;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        struct stm_priv_segment_info_s *pr = get_priv_segment(i);
        if (pr->pub.running_thread != NULL &&
            pr->pub.running_thread != fork_this_tl) {
            fork_abort_thread(i);
        }
    }

    /* Restore a few things: the new pthread_self(), and the %gs
       register */
    int segnum = fork_this_tl->associated_segment_num;
    assert(1 <= segnum && segnum <= NB_SEGMENTS);
    *_get_cpth(fork_this_tl) = pthread_self();
    set_gs_register(get_segment_base(segnum));
    assert(STM_SEGMENT->segment_num == segnum);

    if (!fork_was_in_transaction) {
        stm_commit_transaction();
    }

    /* Done */
    dprintf(("forksupport_child: running one thread now\n"));
}


static void setup_forksupport(void)
{
    static bool fork_support_ready = false;

    if (!fork_support_ready) {
        int res = pthread_atfork(forksupport_prepare, forksupport_parent,
                                 forksupport_child);
        if (res != 0)
            stm_fatalerror("pthread_atfork() failed: %m");
        fork_support_ready = true;
    }
}
