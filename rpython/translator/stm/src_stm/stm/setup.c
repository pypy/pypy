/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


#ifdef USE_REMAP_FILE_PAGES
static char *setup_mmap(char *reason, int *ignored)
{
    char *result = mmap(NULL, TOTAL_MEMORY,
                        PROT_READ | PROT_WRITE,
                        MAP_PAGES_FLAGS, -1, 0);
    if (result == MAP_FAILED)
        stm_fatalerror("%s failed: %m", reason);

    return result;
}
static void close_fd_mmap(int ignored)
{
}
#else
#include <fcntl.h>           /* For O_* constants */
static char *setup_mmap(char *reason, int *map_fd)
{
    char name[128];
    sprintf(name, "/stmgc-c7-bigmem-%ld-%.18e",
            (long)getpid(), get_stm_time());

    /* Create the big shared memory object, and immediately unlink it.
       There is a small window where if this process is killed the
       object is left around.  It doesn't seem possible to do anything
       about it...
    */
    int fd = shm_open(name, O_RDWR | O_CREAT | O_EXCL, 0600);
    shm_unlink(name);

    if (fd == -1) {
        stm_fatalerror("%s failed (stm_open): %m", reason);
    }
    if (ftruncate(fd, TOTAL_MEMORY) != 0) {
        stm_fatalerror("%s failed (ftruncate): %m", reason);
    }
    char *result = mmap(NULL, TOTAL_MEMORY,
                        PROT_READ | PROT_WRITE,
                        MAP_PAGES_FLAGS & ~MAP_ANONYMOUS, fd, 0);
    if (result == MAP_FAILED) {
        stm_fatalerror("%s failed (mmap): %m", reason);
    }
    *map_fd = fd;
    return result;
}
static void close_fd_mmap(int map_fd)
{
    close(map_fd);
}
#endif

static void setup_protection_settings(void)
{
    /* The segment 0 is not used to run transactions, but contains the
       shared copy of the pages.  We mprotect all pages before so that
       accesses fail, up to and including the pages corresponding to the
       nurseries of the other segments. */
    mprotect(stm_object_pages, END_NURSERY_PAGE * 4096UL, PROT_NONE);

    long i;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        char *segment_base = get_segment_base(i);

        /* In each segment, the first page is where TLPREFIX'ed
           NULL accesses land.  We mprotect it so that accesses fail. */
        mprotect(segment_base, 4096, PROT_NONE);

        /* Pages in range(2, FIRST_READMARKER_PAGE) are never used */
        if (FIRST_READMARKER_PAGE > 2)
            mprotect(segment_base + 8192,
                     (FIRST_READMARKER_PAGE - 2) * 4096UL,
                     PROT_NONE);
    }
    pages_setup_readmarkers_for_nursery();
}

void stm_setup(void)
{
    /* Check that some values are acceptable */
    assert(NB_SEGMENTS <= NB_SEGMENTS_MAX);
    assert(CARD_SIZE >= 32 && CARD_SIZE % 16 == 0);
    assert(4096 <= ((uintptr_t)STM_SEGMENT));
    assert((uintptr_t)STM_SEGMENT == (uintptr_t)STM_PSEGMENT);
    assert(((uintptr_t)STM_PSEGMENT) + sizeof(*STM_PSEGMENT) <= 8192);
    assert(2 <= FIRST_READMARKER_PAGE);
    assert(FIRST_READMARKER_PAGE * 4096UL <= READMARKER_START);
    assert(READMARKER_START < READMARKER_END);
    assert(READMARKER_END <= 4096UL * FIRST_OBJECT_PAGE);
    assert(FIRST_OBJECT_PAGE < NB_PAGES);
    assert((NB_PAGES * 4096UL) >> 8 <= (FIRST_OBJECT_PAGE * 4096UL) >> 4);
    assert((END_NURSERY_PAGE * 4096UL) >> 8 <=
           (FIRST_READMARKER_PAGE * 4096UL));
    assert(_STM_FAST_ALLOC <= NB_NURSERY_PAGES * 4096);

    stm_object_pages = setup_mmap("initial stm_object_pages mmap()",
                                  &stm_object_pages_fd);
    setup_protection_settings();

    long i;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        char *segment_base = get_segment_base(i);

        /* Fill the TLS page (page 1) with 0xDC, for debugging */
        memset(REAL_ADDRESS(segment_base, 4096), 0xDC, 4096);
        /* Make a "hole" at STM_PSEGMENT (which includes STM_SEGMENT) */
        memset(REAL_ADDRESS(segment_base, STM_PSEGMENT), 0,
               sizeof(*STM_PSEGMENT));

        /* Initialize STM_PSEGMENT */
        struct stm_priv_segment_info_s *pr = get_priv_segment(i);
        assert(1 <= i && i < 255);   /* 255 is WL_VISITED in gcpage.c */
        pr->write_lock_num = i;
        pr->pub.segment_num = i;
        pr->pub.segment_base = segment_base;
        pr->objects_pointing_to_nursery = NULL;
        pr->old_objects_with_cards = list_create();
        pr->large_overflow_objects = NULL;
        pr->modified_old_objects = list_create();
        pr->modified_old_objects_markers = list_create();
        pr->young_weakrefs = list_create();
        pr->old_weakrefs = list_create();
        pr->young_outside_nursery = tree_create();
        pr->nursery_objects_shadows = tree_create();
        pr->callbacks_on_commit_and_abort[0] = tree_create();
        pr->callbacks_on_commit_and_abort[1] = tree_create();
        pr->overflow_number = GCFLAG_OVERFLOW_NUMBER_bit0 * i;
        highest_overflow_number = pr->overflow_number;
        pr->pub.transaction_read_version = 0xff;
    }

    /* The pages are shared lazily, as remap_file_pages() takes a relatively
       long time for each page.

       The read markers are initially zero, but we set anyway
       transaction_read_version to 0xff in order to force the first
       transaction to "clear" the read markers by mapping a different,
       private range of addresses.
    */

    setup_sync();
    setup_nursery();
    setup_gcpage();
    setup_pages();
    setup_forksupport();
}

void stm_teardown(void)
{
    /* This function is called during testing, but normal programs don't
       need to call it. */
    assert(!_has_mutex());

    long i;
    for (i = 1; i <= NB_SEGMENTS; i++) {
        struct stm_priv_segment_info_s *pr = get_priv_segment(i);
        assert(pr->objects_pointing_to_nursery == NULL);
        list_free(pr->old_objects_with_cards);
        assert(pr->large_overflow_objects == NULL);
        list_free(pr->modified_old_objects);
        list_free(pr->modified_old_objects_markers);
        list_free(pr->young_weakrefs);
        list_free(pr->old_weakrefs);
        tree_free(pr->young_outside_nursery);
        tree_free(pr->nursery_objects_shadows);
        tree_free(pr->callbacks_on_commit_and_abort[0]);
        tree_free(pr->callbacks_on_commit_and_abort[1]);
    }

    munmap(stm_object_pages, TOTAL_MEMORY);
    stm_object_pages = NULL;
    close_fd_mmap(stm_object_pages_fd);

    teardown_core();
    teardown_sync();
    teardown_gcpage();
    teardown_pages();
}

static void _shadowstack_trap_page(char *start, int prot)
{
    size_t bsize = STM_SHADOW_STACK_DEPTH * sizeof(struct stm_shadowentry_s);
    char *end = start + bsize + 4095;
    end -= (((uintptr_t)end) & 4095);
    mprotect(end, 4096, prot);
}

static void _init_shadow_stack(stm_thread_local_t *tl)
{
    size_t bsize = STM_SHADOW_STACK_DEPTH * sizeof(struct stm_shadowentry_s);
    char *start = malloc(bsize + 8192);  /* for the trap page, plus rounding */
    if (!start)
        stm_fatalerror("can't allocate shadow stack");

    /* set up a trap page: if the shadowstack overflows, it will
       crash in a clean segfault */
    _shadowstack_trap_page(start, PROT_NONE);

    struct stm_shadowentry_s *s = (struct stm_shadowentry_s *)start;
    tl->shadowstack = s;
    tl->shadowstack_base = s;
    STM_PUSH_ROOT(*tl, -1);
}

static void _done_shadow_stack(stm_thread_local_t *tl)
{
    assert(tl->shadowstack > tl->shadowstack_base);
    assert(tl->shadowstack_base->ss == (object_t *)-1);

    char *start = (char *)tl->shadowstack_base;
    _shadowstack_trap_page(start, PROT_READ | PROT_WRITE);

    free(tl->shadowstack_base);
    tl->shadowstack = NULL;
    tl->shadowstack_base = NULL;
}

static pthread_t *_get_cpth(stm_thread_local_t *tl)
{
    assert(sizeof(pthread_t) <= sizeof(tl->creating_pthread));
    return (pthread_t *)(tl->creating_pthread);
}

void stm_register_thread_local(stm_thread_local_t *tl)
{
    int num;
    s_mutex_lock();
    if (stm_all_thread_locals == NULL) {
        stm_all_thread_locals = tl->next = tl->prev = tl;
        num = 0;
    }
    else {
        tl->next = stm_all_thread_locals;
        tl->prev = stm_all_thread_locals->prev;
        stm_all_thread_locals->prev->next = tl;
        stm_all_thread_locals->prev = tl;
        num = tl->prev->associated_segment_num;
    }
    tl->thread_local_obj = NULL;
    tl->_timing_cur_state = STM_TIME_OUTSIDE_TRANSACTION;
    tl->_timing_cur_start = get_stm_time();

    /* assign numbers consecutively, but that's for tests; we could also
       assign the same number to all of them and they would get their own
       numbers automatically. */
    num = (num % NB_SEGMENTS) + 1;
    tl->associated_segment_num = num;
    *_get_cpth(tl) = pthread_self();
    _init_shadow_stack(tl);
    set_gs_register(get_segment_base(num));
    s_mutex_unlock();
}

void stm_unregister_thread_local(stm_thread_local_t *tl)
{
    s_mutex_lock();
    assert(tl->prev != NULL);
    assert(tl->next != NULL);
    _done_shadow_stack(tl);
    if (tl == stm_all_thread_locals) {
        stm_all_thread_locals = stm_all_thread_locals->next;
        if (tl == stm_all_thread_locals) {
            stm_all_thread_locals = NULL;
            s_mutex_unlock();
            return;
        }
    }
    tl->prev->next = tl->next;
    tl->next->prev = tl->prev;
    tl->prev = NULL;
    tl->next = NULL;
    s_mutex_unlock();
}

__attribute__((unused))
static bool _is_tl_registered(stm_thread_local_t *tl)
{
    return tl->next != NULL;
}
