/* Imported by rpython/translator/stm/import_stmgc.py */
#include "stmimpl.h"


/* In this file, we use size_t to measure various sizes that can poten-
 * tially be large.  Be careful that it's an unsigned type --- but it
 * is needed to represent more than 2GB on 32-bit machines (up to 4GB).
 */

/* This maps each small request size to the number of blocks of this size
   that fit in a page. */
static int nblocks_for_size[GC_SMALL_REQUESTS];

/* A mutex for major collections and other global operations */
static pthread_mutex_t mutex_gc_lock = PTHREAD_MUTEX_INITIALIZER;

/* A count-down: when it reaches 0, run the next major collection */
static revision_t countdown_next_major_coll = GC_MIN;

/* For statistics */
static size_t count_global_pages;

/* Only computed during a major collection */
static size_t mc_total_in_use, mc_total_reserved;

/* For tests */
long stmgcpage_count(int quantity)
{
    switch (quantity) {
    case 0: return count_global_pages;
    case 1: return LOCAL_GCPAGES()->count_pages;
    case 2: count_global_pages = 0; return 0;
    default: return -1;
    }
}


/***** Support code *****/

void stmgcpage_acquire_global_lock(void)
{
    int err = pthread_mutex_lock(&mutex_gc_lock);
    if (err != 0)
        stm_fatalerror("stmgcpage_acquire_global_lock: "
                       "pthread_mutex_lock() failure\n");
}

void stmgcpage_release_global_lock(void)
{
    int err = pthread_mutex_unlock(&mutex_gc_lock);
    if (err != 0)
        stm_fatalerror("stmgcpage_release_global_lock: "
                       "pthread_mutex_unlock() failure\n");
}


/***** Initialization logic *****/

static void init_global_data(void)
{
    int i;
    for (i = 1; i < GC_SMALL_REQUESTS; i++) {
        nblocks_for_size[i] =
            (GC_PAGE_SIZE - sizeof(page_header_t)) / (WORD * i);
    }
}

void stmgcpage_init_tls(void)
{
    if (nblocks_for_size[1] == 0)
        init_global_data();

    /* Take back ownership of the pages currently assigned to
       LOCAL_GCPAGES that might come from a previous thread. */
}

void stmgcpage_done_tls(void)
{
    /* Send to the shared area all my pages.  For now we don't extract
       the information about which locations are free or not; we just
       leave it to the next major GC to figure them out. */
}


/***** Thread-local allocator *****/

void stmgcpage_reduce_threshold(size_t size)
{
    revision_t next, target;
 restart:
    next = ACCESS_ONCE(countdown_next_major_coll);
    if (next >= size) {
        target = next - size;
    }
    else {
        /* we cannot do right now a major collection, but we can speed up
           the time of the next minor collection (which will be followed
           by a major collection) */
        target = 0;
        stmgc_minor_collect_soon();
    }
    if (!bool_cas(&countdown_next_major_coll, next, target))
        goto restart;
}

static char *alloc_tracked_memory(size_t size)
{
    /* Adjust the threshold; the caller is responsible for detecting the
       condition that the threshold reached 0. */
    stmgcpage_reduce_threshold(size);

    char *result = stm_malloc(size);
    if (!result) {
        stm_fatalerror("alloc_tracked_memory: out of memory "
                       "allocating %zu bytes\n", size);
    }
    return result;
}

static gcptr allocate_new_page(int size_class)
{
    /* Allocate and return a new page for the given size_class. */
    page_header_t *page = (page_header_t *)alloc_tracked_memory(GC_PAGE_SIZE);

    struct tx_public_descriptor *gcp = LOCAL_GCPAGES();
    gcp->count_pages++;
    count_global_pages++;

    /* Initialize the fields of the resulting page */
    page->next_page = gcp->pages_for_size[size_class];
    gcp->pages_for_size[size_class] = page;

    /* Initialize the chained list in the page */
    gcptr head = (gcptr)(page + 1);
    gcptr current, next;
    int count = nblocks_for_size[size_class];
    int nsize = size_class * WORD;
    int i;
    current = head;
    for (i = 0; i < count - 1; i++) {
        next = (gcptr)(((char *)current) + nsize);
        assert(!(GCFLAG_VISITED & DEBUG_WORD(0xDD)));
        current->h_tid = DEBUG_WORD(0xDD);  /*anything without GCFLAG_VISITED*/
        current->h_revision = (revision_t)next;
        //stm_dbgmem_not_used(current, nsize, 0);
        current = next;
    }
    current->h_tid = DEBUG_WORD(0xDD);
    current->h_revision = (revision_t)gcp->free_loc_for_size[size_class];
    //stm_dbgmem_not_used(current, nsize, 0);
    gcp->free_loc_for_size[size_class] = head;
    return head;
}

gcptr stmgcpage_malloc(size_t size)
{
    /* Allocates an object of the given 'size'.  This will never run
       a collection: you need to call stmgcpage_possibly_major_collect(0)
       when you know you're at a safe point. */
    struct tx_public_descriptor *gcp = LOCAL_GCPAGES();

    if (size <= GC_SMALL_REQUEST_THRESHOLD) {
        gcptr result;
        int size_class = (size + WORD - 1) / WORD;
        assert(0 < size_class && size_class < GC_SMALL_REQUESTS);

        /* The result is simply 'free_loc_for_size[size_class]' */
        result = gcp->free_loc_for_size[size_class];
        if (!result) {
            result = allocate_new_page(size_class);
        }
        gcp->free_loc_for_size[size_class] = (gcptr)result->h_revision;
        //stm_dbgmem_used_again(result, size_class * WORD, 0);
        dprintf(("stmgcpage_malloc(%zu): %p\n", size, result));
        return result;
    }
    else {
        gcptr result = (gcptr)alloc_tracked_memory(size);
        dprintf(("stmgcpage_malloc(BIG %zu): %p\n", size, result));
        g2l_insert(&gcp->nonsmall_objects, result, result);
        return result;
    }
}

#ifndef NDEBUG
static unsigned char random_char = 0x55;
#endif

void stmgcpage_free(gcptr obj)
{
    size_t size = stmgc_size(obj);
    struct tx_public_descriptor *gcp = LOCAL_GCPAGES();

    if (size <= GC_SMALL_REQUEST_THRESHOLD) {
        int size_class = (size + WORD - 1) / WORD;
        assert(0 < size_class && size_class < GC_SMALL_REQUESTS);

        /* We simply re-add the object to the right chained list */
        assert(obj->h_tid = DEBUG_WORD(random_char));
        assert(random_char ^= (0xAA ^ 0x55));
        obj->h_revision = (revision_t)gcp->free_loc_for_size[size_class];
        gcp->free_loc_for_size[size_class] = obj;
        //stm_dbgmem_not_used(obj, size_class * WORD, 0);
    }
    else {
        g2l_delete_item(&gcp->nonsmall_objects, obj);
        stm_free(obj, size);
    }
}


/***** Major collections: marking *****/

static struct GcPtrList objects_to_trace;

static void visit(gcptr *pobj)
{
    gcptr obj = *pobj;
    if (obj == NULL)
        return;

 restart:
    if (obj->h_tid & GCFLAG_VISITED) {
        dprintf(("[already visited: %p]\n", obj));
        assert(obj == *pobj);
        assert((obj->h_revision & 3) ||   /* either odd, or stub */
               (obj->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED));
        return;    /* already seen */
    }

    if (obj->h_revision & 1) {
        assert(!(obj->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED));
        obj->h_tid &= ~GCFLAG_PUBLIC_TO_PRIVATE;  /* see also fix_outdated() */
    }
    else if (obj->h_tid & GCFLAG_PUBLIC) {
        /* h_revision is a ptr: we have a more recent version */
        gcptr prev_obj = obj;

        if (!(obj->h_revision & 2)) {
            /* go visit the more recent version */
            obj = (gcptr)obj->h_revision;
        }
        else {
            /* it's a stub: keep it if it points to a protected version,
               because we need to keep the effect of stealing if it is
               later accessed by the wrong thread.  If it points to a
               public object (possibly outdated), we can ignore the stub.
            */
            assert(obj->h_tid & GCFLAG_STUB);
            obj = (gcptr)(obj->h_revision - 2);
            if (!(obj->h_tid & GCFLAG_PUBLIC)) {
                prev_obj->h_tid |= GCFLAG_VISITED;
                assert(*pobj == prev_obj);
                gcptr obj1 = obj;
                visit(&obj1);       /* recursion, but should be only once */
                assert(prev_obj->h_tid & GCFLAG_STUB);
                prev_obj->h_revision = ((revision_t)obj1) | 2;
                return;
            }
        }

        if (!(obj->h_revision & 3)) {
            obj = (gcptr)obj->h_revision;
            assert(obj->h_tid & GCFLAG_PUBLIC);
            prev_obj->h_revision = (revision_t)obj;
        }
        *pobj = obj;
        goto restart;
    }
    else {
        assert(obj->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED);
        gcptr B = (gcptr)obj->h_revision;
        gcptrlist_insert(&objects_to_trace, B);

        if (!(B->h_tid & GCFLAG_PUBLIC)) {
            /* a regular private_from_protected object with a backup copy B */
            assert(B->h_tid & GCFLAG_BACKUP_COPY);
            assert(B->h_revision & 1);
            B->h_tid |= GCFLAG_VISITED;
        }
        else {
            /* a private_from_protected with a stolen backup copy B */
            assert(!(B->h_tid & GCFLAG_BACKUP_COPY));
            gcptr obj1 = B;
            visit(&obj1);     /* xxx recursion? */
            obj->h_revision = (revision_t)obj1;
        }
    }
    obj->h_tid |= GCFLAG_VISITED;
    gcptrlist_insert(&objects_to_trace, obj);
}

static void visit_all_objects(void)
{
    while (gcptrlist_size(&objects_to_trace) > 0) {
        gcptr obj = gcptrlist_pop(&objects_to_trace);
        stmgc_trace(obj, &visit);
    }
}

static void mark_prebuilt_roots(void)
{
    /* Note about prebuilt roots: 'stm_prebuilt_gcroots' is a list that
       contains all the ones that have been modified.  Because they are
       themselves not in any page managed by this file, their
       GCFLAG_VISITED will not be removed at the end of the current
       collection.  This is fine because the base object cannot contain
       references to the heap.  So we decided to systematically set
       GCFLAG_VISITED on prebuilt objects. */
    gcptr *pobj = stm_prebuilt_gcroots.items;
    gcptr *pend = stm_prebuilt_gcroots.items + stm_prebuilt_gcroots.size;
    gcptr obj;
    for (; pobj != pend; pobj++) {
        obj = *pobj;
        assert(obj->h_tid & GCFLAG_PREBUILT_ORIGINAL);
        obj->h_tid &= ~GCFLAG_VISITED;
        assert(IS_POINTER(obj->h_revision));
        visit((gcptr *)&obj->h_revision);
    }
}

static void mark_roots(gcptr *root, gcptr *end)
{
    //assert(*root == END_MARKER);
    //root++;
    while (root != end) {
        gcptr o = *root;
        visit(root);
        dprintf(("visit stack root: %p -> %p\n", o, *root));
        (void)o;   /* silence "warning: unused variable 'o'" */
        root++;
    }
}

static void mark_all_stack_roots(void)
{
    struct tx_descriptor *d;
    for (d = stm_tx_head; d; d = d->tx_next) {

        /* the roots pushed on the shadowstack */
        mark_roots(d->shadowstack, *d->shadowstack_end_ref);

        /* the thread-local object */
        visit(d->thread_local_obj_ref);
        visit(&d->old_thread_local_obj);

        /* the current transaction's private copies of public objects */
        wlog_t *item;
        G2L_LOOP_FORWARD(d->public_to_private, item) {

            /* note that 'item->addr' is also in the read set, so if it was
               outdated, it will be found at that time */
            visit(&item->addr);
            visit(&item->val);

        } G2L_LOOP_END;

        /* make sure that the other lists are empty */
        assert(gcptrlist_size(&d->public_with_young_copy) == 0);
        assert(gcptrlist_size(&d->public_descriptor->stolen_objects) == 0);
        assert(gcptrlist_size(&d->public_descriptor->stolen_young_stubs) == 0);
        /* NOT NECESSARILY EMPTY:
           - list_of_read_objects
           - private_from_protected
           - public_to_private
           - old_objects_to_trace
        */
        assert(gcptrlist_size(&d->list_of_read_objects) ==
               d->num_read_objects_known_old);
        assert(gcptrlist_size(&d->private_from_protected) ==
               d->num_private_from_protected_known_old);
    }
}

static void cleanup_for_thread(struct tx_descriptor *d)
{
    long i;
    gcptr *items;

    /* It can occur that 'private_from_protected' contains an object that
     * has not been visited at all (maybe only in inevitable
     * transactions). 
     */
    items = d->private_from_protected.items;
    for (i = d->private_from_protected.size - 1; i >= 0; i--) {
        gcptr obj = items[i];
        assert(obj->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED);

        if (!(obj->h_tid & GCFLAG_VISITED)) {
            /* forget 'obj' */
            items[i] = items[--d->private_from_protected.size];
        }
    }

    /* If we're aborting this transaction anyway, we don't need to do
     * more here.
     */
    if (d->active < 0)
        return;       /* already "aborted" during forced minor collection */

    if (d->active == 2) {
        /* inevitable transaction: clear the list of read objects */
        gcptrlist_clear(&d->list_of_read_objects);
    }

    items = d->list_of_read_objects.items;
    for (i = d->list_of_read_objects.size - 1; i >= 0; --i) {
        gcptr obj = items[i];
        assert(!(obj->h_tid & GCFLAG_STUB));

        /* Warning: in case the object listed is outdated and has been
           replaced with a more recent revision, then it might be the
           case that obj->h_revision doesn't have GCFLAG_VISITED, but
           just removing it is very wrong --- we want 'd' to abort.
        */
        if (obj->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED) {
            assert(IS_POINTER(obj->h_revision));
            obj = (gcptr)obj->h_revision;
        }

        revision_t v = obj->h_revision;
        if (IS_POINTER(v)) {
            /* has a more recent revision.  Oups. */
            dprintf(("ABRT_COLLECT_MAJOR %p: "
                     "%p was read but modified already\n", d, obj));
            AbortTransactionAfterCollect(d, ABRT_COLLECT_MAJOR);
            return;
        }

        /* It should not be possible to see a non-visited object in the
           read list.  I think the only case is: the transaction is
           inevitable, and since it started, it popped objects out of
           its shadow stack.  Some popped objects might become free even
           if they have been read from.  But for inevitable transactions,
           we clear the 'list_of_read_objects' above anyway.
           
           However, some situations can occur (I believe) only in tests.
           To be on the safe side, do the right thing and unlist the
           non-visited object.
           */
        if (!(obj->h_tid & GCFLAG_VISITED)) {
            items[i] = items[--d->list_of_read_objects.size];
        }
    }

    d->num_read_objects_known_old = d->list_of_read_objects.size;

    /* We are now after visiting all objects, and we know the
     * transaction isn't aborting because of this collection.  We have
     * cleared GCFLAG_PUBLIC_TO_PRIVATE from public objects at the end
     * of the chain.  Now we have to set it again on public objects that
     * have a private copy.
     */
    wlog_t *item;

    dprintf(("fix public_to_private on thread %p\n", d));

    G2L_LOOP_FORWARD(d->public_to_private, item) {

        assert(item->addr->h_tid & GCFLAG_PUBLIC);
        /* assert(is_private(item->val)); but in the other thread,
           which becomes: */
        assert((item->val->h_revision == *d->private_revision_ref) ||
               (item->val->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED));

        item->addr->h_tid |= GCFLAG_PUBLIC_TO_PRIVATE;
        dprintf(("\tpublic_to_private: %p\n", item->addr));

    } G2L_LOOP_END;
}

static void clean_up_lists_of_read_objects_and_fix_outdated_flags(void)
{
    struct tx_descriptor *d;
    for (d = stm_tx_head; d; d = d->tx_next)
        cleanup_for_thread(d);
}


/***** Major collections: sweeping *****/

static void sweep_pages(struct tx_public_descriptor *gcp, int size_class)
{
    int objs_per_page = nblocks_for_size[size_class];
    revision_t obj_size = size_class * WORD;
    gcptr freelist = NULL;
    page_header_t *lpage, *lpagenext;
    page_header_t *surviving_pages = NULL;
    int j;
    gcptr p;

    for (lpage = gcp->pages_for_size[size_class]; lpage; lpage = lpagenext) {
        lpagenext = lpage->next_page;
        /* sweep 'page': any object with GCFLAG_VISITED stays alive
           and the flag is removed; other locations are marked as free. */
        p = (gcptr)(lpage + 1);
        for (j = 0; j < objs_per_page; j++) {
            if (p->h_tid & GCFLAG_VISITED)
                break;  /* first object that stays alive */
            p = (gcptr)(((char *)p) + obj_size);
        }
        if (j < objs_per_page) {
            /* the page contains at least one object that stays alive */
            lpage->next_page = surviving_pages;
            surviving_pages = lpage;
            p = (gcptr)(lpage + 1);
            for (j = 0; j < objs_per_page; j++) {
                if (p->h_tid & GCFLAG_VISITED) {
                    p->h_tid &= ~GCFLAG_VISITED;
                    mc_total_in_use += obj_size;
                }
                else {
#ifdef DUMP_EXTRA
                    if (p->h_tid != DEBUG_WORD(0xDD)) {
                        dprintf(("| freeing %p\n", p));
                    }
#endif
                    /* skip the assignment if compiled without asserts */
                    assert(!(GCFLAG_VISITED & DEBUG_WORD(0xDD)));
                    assert(p->h_tid = DEBUG_WORD(0xDD));
                    p->h_revision = (revision_t)freelist;
                    //stm_dbgmem_not_used(p, size_class * WORD, 0);
                    freelist = p;
                }
                p = (gcptr)(((char *)p) + obj_size);
            }
            mc_total_reserved += obj_size * objs_per_page;
        }
        else {
            /* the page is fully free */
#ifdef DUMP_EXTRA
            p = (gcptr)(lpage + 1);
            for (j = 0; j < objs_per_page; j++) {
                assert(!(p->h_tid & GCFLAG_VISITED));
                if (p->h_tid != DEBUG_WORD(0xDD)) {
                    dprintf(("| freeing %p (with page %p)\n", p, lpage));
                }
                p = (gcptr)(((char *)p) + obj_size);
            }
#endif
            stm_free(lpage, GC_PAGE_SIZE);
            assert(gcp->count_pages > 0);
            assert(count_global_pages > 0);
            gcp->count_pages--;
            count_global_pages--;
        }
    }
    gcp->pages_for_size[size_class] = surviving_pages;
    gcp->free_loc_for_size[size_class] = freelist;
}

static void free_unused_local_pages(struct tx_public_descriptor *gcp)
{
    int i;
    wlog_t *item;

    for (i = 1; i < GC_SMALL_REQUESTS; i++) {
        sweep_pages(gcp, i);
    }

    G2L_LOOP_FORWARD(gcp->nonsmall_objects, item) {

        gcptr p = item->addr;
        if (p->h_tid & GCFLAG_VISITED) {
            p->h_tid &= ~GCFLAG_VISITED;
        }
        else {
            G2L_LOOP_DELETE(item);
            stm_free(p, stmgc_size(p));
        }

    } G2L_LOOP_END_AND_COMPRESS;
}

static void free_all_unused_local_pages(void)
{
    struct tx_descriptor *d;
    for (d = stm_tx_head; d; d = d->tx_next) {
        free_unused_local_pages(d->public_descriptor);
    }
}

static void free_closed_thread_descriptors(void)
{
    struct tx_public_descriptor *gcp;
    revision_t index = -1;

    while ((gcp = stm_get_free_public_descriptor(&index)) != NULL) {

        free_unused_local_pages(gcp);

        assert(gcp->collection_lock == 0);
        assert(gcp->stolen_objects.size == 0);
        assert(gcp->stolen_young_stubs.size == 0);
        gcptrlist_delete(&gcp->stolen_objects);
        gcptrlist_delete(&gcp->stolen_young_stubs);
    }
}


/***** Major collections: forcing minor collections *****/

void force_minor_collections(void)
{
    struct tx_descriptor *d;
    struct tx_descriptor *saved = thread_descriptor;
    revision_t saved_private_rev = stm_private_rev_num;
    char *saved_read_barrier_cache = stm_read_barrier_cache;

    assert(saved_private_rev == *saved->private_revision_ref);
    assert(saved_read_barrier_cache == *saved->read_barrier_cache_ref);

    for (d = stm_tx_head; d; d = d->tx_next) {
        /* Force a minor collection to run in the thread 'd'.
           Usually not needed, but it may be the case that this major
           collection was not preceeded by a minor collection if the
           thread is busy in a system call for example.
        */
        if (d != saved) {
            /* Hack: temporarily pretend that we "are" the other thread...
             */
            thread_descriptor = d;
            stm_private_rev_num = *d->private_revision_ref;
            stm_read_barrier_cache = *d->read_barrier_cache_ref;

            stmgc_minor_collect_no_abort();

            assert(stm_private_rev_num == *d->private_revision_ref);
            *d->read_barrier_cache_ref = stm_read_barrier_cache;

            thread_descriptor = saved;
            stm_private_rev_num = saved_private_rev;
            stm_read_barrier_cache = saved_read_barrier_cache;
        }
    }
    stmgc_minor_collect_no_abort();
}


/***** Major collections: main *****/

void update_next_threshold(void)
{
    uintptr_t free_space_in_pages, next;

    /* the limit will be reached when we have allocated 0.82 times mc_total */
    next = (uintptr_t)(mc_total_in_use * (GC_MAJOR_COLLECT-1.0));

    /* this limit should be at least GC_MIN */
    if (next < GC_MIN)
        next = GC_MIN;

    /* this difference gives the size allocated in pages but unused so far */
    assert(mc_total_in_use <= mc_total_reserved);
    free_space_in_pages = mc_total_reserved - mc_total_in_use;

    /* decrement 'next' by this much, because it will not be accounted for */
    if (next >= free_space_in_pages)
        next -= free_space_in_pages;
    else
        next = 0;

    /* allow for headroom: enforce the smallest allowed value */
    if (next < GC_EXPAND)
        next = GC_EXPAND;

    /* done */
    countdown_next_major_coll = next;
}

static void major_collect(void)
{
    stmgcpage_acquire_global_lock();
    dprintf((",-----\n| running major collection...\n"));

    force_minor_collections();

    assert(gcptrlist_size(&objects_to_trace) == 0);
    mark_prebuilt_roots();
    mark_all_stack_roots();
    visit_all_objects();
    gcptrlist_delete(&objects_to_trace);
    clean_up_lists_of_read_objects_and_fix_outdated_flags();

    mc_total_in_use = mc_total_reserved = 0;
    free_all_unused_local_pages();
#if 0
    free_unused_global_pages();
#endif
    free_closed_thread_descriptors();
    update_next_threshold();

    dprintf(("| %lu bytes alive, %lu not used, countdown %lu\n`-----\n",
             (unsigned long)mc_total_in_use,
             (unsigned long)(mc_total_reserved - mc_total_in_use),
             (unsigned long)countdown_next_major_coll));
    stmgcpage_release_global_lock();
}

void stmgcpage_possibly_major_collect(int force)
{
    if (force)
        stmgcpage_reduce_threshold((size_t)-1);

    /* If 'countdown_next_major_coll' reached 0, then run a major coll now. */
    if (ACCESS_ONCE(countdown_next_major_coll) > 0)
        return;

    stm_start_single_thread();

    /* If several threads were blocked on the previous line, the first
       one to proceed sees 0 in 'countdown_next_major_coll'.  It's the
       thread that will do the major collection.  Afterwards the other
       threads will also acquire the RW lock in exclusive mode, but won't
       do anything. */
    if (countdown_next_major_coll == 0)
        major_collect();

    stm_stop_single_thread();

    AbortNowIfDelayed();
}
