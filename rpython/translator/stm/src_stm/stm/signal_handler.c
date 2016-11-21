/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif


static void setup_signal_handler(void)
{
    struct sigaction act;
    memset(&act, 0, sizeof(act));

	act.sa_sigaction = &_signal_handler;
	/* The SA_SIGINFO flag tells sigaction() to use the sa_sigaction field, not sa_handler. */
	act.sa_flags = SA_SIGINFO | SA_NODEFER;

	if (sigaction(SIGSEGV, &act, NULL) < 0) {
		perror ("sigaction");
		abort();
	}
}


static void copy_bk_objs_in_page_from(int from_segnum, uintptr_t pagenum,
                                      bool only_if_not_modified)
{
    /* looks at all bk copies of objects overlapping page 'pagenum' and
       copies the part in 'pagenum' back to the current segment */
    dprintf(("copy_bk_objs_in_page_from(%d, %ld, %d)\n",
             from_segnum, (long)pagenum, only_if_not_modified));

    assert(modification_lock_check_rdlock(from_segnum));
    struct list_s *list = get_priv_segment(from_segnum)->modified_old_objects;
    struct stm_undo_s *undo = (struct stm_undo_s *)list->items;
    struct stm_undo_s *end = (struct stm_undo_s *)(list->items + list->count);

    import_objects(only_if_not_modified ? -2 : -1,
                   pagenum, undo, end);
}

static void go_to_the_past(uintptr_t pagenum,
                           struct stm_commit_log_entry_s *from,
                           struct stm_commit_log_entry_s *to)
{
    assert(modification_lock_check_wrlock(STM_SEGMENT->segment_num));
    assert(from->rev_num >= to->rev_num);
    /* walk BACKWARDS the commit log and update the page 'pagenum',
       initially at revision 'from', until we reach the revision 'to'. */

    /* XXXXXXX Recursive algo for now, fix this! */
    if (from != to) {
        struct stm_commit_log_entry_s *cl = to->next;
        go_to_the_past(pagenum, from, cl);

        struct stm_undo_s *undo = cl->written;
        struct stm_undo_s *end = cl->written + cl->written_count;

        import_objects(-1, pagenum, undo, end);
    }
}



static void handle_segfault_in_page(uintptr_t pagenum)
{
    /* assumes page 'pagenum' is ACCESS_NONE, privatizes it,
       and validates to newest revision */

    dprintf(("handle_segfault_in_page(%lu), seg %d\n", pagenum, STM_SEGMENT->segment_num));

    /* XXX: bad, but no deadlocks: */
    acquire_all_privatization_locks();

    long i;
    int my_segnum = STM_SEGMENT->segment_num;

    assert(get_page_status_in(my_segnum, pagenum) == PAGE_NO_ACCESS);

    /* find who has the most recent revision of our page */
    int copy_from_segnum = -1;
    uint64_t most_recent_rev = 0;
    for (i = 1; i < NB_SEGMENTS; i++) {
        if (i == my_segnum)
            continue;

        struct stm_commit_log_entry_s *log_entry;
        log_entry = get_priv_segment(i)->last_commit_log_entry;
        if (get_page_status_in(i, pagenum) != PAGE_NO_ACCESS
            && (copy_from_segnum == -1 || log_entry->rev_num > most_recent_rev)) {
            copy_from_segnum = i;
            most_recent_rev = log_entry->rev_num;
        }
    }
    OPT_ASSERT(copy_from_segnum != my_segnum);

    /* make our page write-ready */
    page_mark_accessible(my_segnum, pagenum);

    /* account for this page now: XXX */
    /* increment_total_allocated(4096); */

    if (copy_from_segnum == -1) {
        /* this page is only accessible in the sharing segment seg0 so far (new
           allocation). We can thus simply mark it accessible here. */
        pagecopy(get_virtual_page(my_segnum, pagenum),
                 get_virtual_page(0, pagenum));
        release_all_privatization_locks();
        return;
    }

    /* before copying anything, acquire modification locks from our and
       the other segment */
    uint64_t to_lock = (1UL << copy_from_segnum);
    acquire_modification_lock_set(to_lock, my_segnum);
    pagecopy(get_virtual_page(my_segnum, pagenum),
             get_virtual_page(copy_from_segnum, pagenum));

    /* if there were modifications in the page, revert them. */
    copy_bk_objs_in_page_from(copy_from_segnum, pagenum, false);

    /* we need to go from 'src_version' to 'target_version'.  This
       might need a walk into the past. */
    struct stm_commit_log_entry_s *src_version, *target_version;
    src_version = get_priv_segment(copy_from_segnum)->last_commit_log_entry;
    target_version = STM_PSEGMENT->last_commit_log_entry;


    dprintf(("handle_segfault_in_page: rev %lu to rev %lu\n",
             src_version->rev_num, target_version->rev_num));
    /* adapt revision of page to our revision:
       if our rev is higher than the page we copy from, everything
       is fine as we never read/modified the page anyway
     */
    if (src_version->rev_num > target_version->rev_num)
        go_to_the_past(pagenum, src_version, target_version);

    release_modification_lock_set(to_lock, my_segnum);
    release_all_privatization_locks();
}

static void _signal_handler(int sig, siginfo_t *siginfo, void *context)
{
    assert(_stm_segfault_expected > 0);

    int saved_errno = errno;
    char *addr = siginfo->si_addr;
    dprintf(("si_addr: %p\n", addr));
    if (addr == NULL || addr < stm_object_pages ||
        addr >= stm_object_pages+TOTAL_MEMORY) {
        /* actual segfault, unrelated to stmgc */
        fprintf(stderr, "Segmentation fault: accessing %p\n", addr);
        detect_shadowstack_overflow(addr);
        abort();
    }

    int segnum = get_segment_of_linear_address(addr);
    OPT_ASSERT(segnum != 0);
    if (segnum != STM_SEGMENT->segment_num) {
        fprintf(stderr, "Segmentation fault: accessing %p (seg %d) from"
                " seg %d\n", addr, segnum, STM_SEGMENT->segment_num);
        abort();
    }
    dprintf(("-> segment: %d\n", segnum));

    char *seg_base = STM_SEGMENT->segment_base;
    uintptr_t pagenum = ((char*)addr - seg_base) / 4096UL;
    if (pagenum < END_NURSERY_PAGE) {
        fprintf(stderr, "Segmentation fault: accessing %p (seg %d "
                        "page %lu)\n", addr, segnum, pagenum);
        abort();
    }

    DEBUG_EXPECT_SEGFAULT(false);
    handle_segfault_in_page(pagenum);
    DEBUG_EXPECT_SEGFAULT(true);

    errno = saved_errno;
    /* now return and retry */
}
