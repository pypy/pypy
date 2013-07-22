/* Imported by rpython/translator/stm/import_stmgc.py */
#include "stmimpl.h"

int stmgc_is_in_nursery(struct tx_descriptor *d, gcptr obj)
{
    return (d->nursery_base <= (char*)obj && ((char*)obj) < d->nursery_end);
}

size_t stmgc_size(gcptr obj)
{
    assert(!(obj->h_tid & GCFLAG_STUB));
    return stmcb_size(obj);
}

void stmgc_trace(gcptr obj, void visit(gcptr *))
{
    assert(!(obj->h_tid & GCFLAG_STUB));
    stmcb_trace(obj, visit);
}

/* forward declarations */
#ifndef NDEBUG
static int minor_collect_anything_to_do(struct tx_descriptor *);
#endif
static gcptr allocate_next_section(size_t size, revision_t tid);

/************************************************************/

void stmgc_init_nursery(void)
{
    struct tx_descriptor *d = thread_descriptor;

    assert(d->nursery_base == NULL);
    d->nursery_base = stm_malloc(GC_NURSERY);       /* start of nursery */
    d->nursery_end = d->nursery_base + GC_NURSERY;  /* end of nursery */
    d->nursery_current = d->nursery_base;           /* current position */
    d->nursery_nextlimit = d->nursery_base;         /* next section limit */
    d->nursery_cleared = NC_REGULAR;

    dprintf(("minor: nursery is at [%p to %p]\n", d->nursery_base,
             d->nursery_end));
}

void stmgc_done_nursery(void)
{
    struct tx_descriptor *d = thread_descriptor;
    /* someone may have called minor_collect_soon()
       inbetween the preceeding minor_collect() and 
       this assert (committransaction() -> 
       updatechainheads() -> stub_malloc() -> ...): */
    assert(!minor_collect_anything_to_do(d)
           || d->nursery_current == d->nursery_end);
    stm_free(d->nursery_base, GC_NURSERY);

    gcptrlist_delete(&d->old_objects_to_trace);
    gcptrlist_delete(&d->public_with_young_copy);
    gcptrlist_delete(&d->young_weakrefs);
}

void stmgc_minor_collect_soon(void)
{
    struct tx_descriptor *d = thread_descriptor;
    d->nursery_current = d->nursery_end;
}

inline static gcptr allocate_nursery(size_t size, revision_t tid)
{
    /* if 'tid == -1', we must not collect */
    struct tx_descriptor *d = thread_descriptor;
    gcptr P;
    char *cur = d->nursery_current;
    char *end = cur + size;
    assert((size & 3) == 0);
    d->nursery_current = end;
    if (end > d->nursery_nextlimit) {
        P = allocate_next_section(size, tid);
    }
    else {
        P = (gcptr)cur;
        P->h_tid = tid;
    }
#ifdef _GC_DEBUG
    if (P != NULL) {
        assert(P->h_tid != 0);
        assert_cleared(((char *)P) + sizeof(revision_t),
                       size - sizeof(revision_t));
    }
    else
        assert(tid == -1);
#endif
    return P;
}

gcptr stm_allocate(size_t size, unsigned long tid)
{
    /* XXX inline the fast path */
    assert(tid == (tid & STM_USER_TID_MASK));
    gcptr P = allocate_nursery(size, tid);
    P->h_revision = stm_private_rev_num;
    assert(P->h_original == 0);  /* null-initialized already */
    return P;
}

gcptr stm_allocate_immutable(size_t size, unsigned long tid)
{
    gcptr P = stm_allocate(size, tid);
    P->h_tid |= GCFLAG_IMMUTABLE;
    return P;
}

gcptr stmgc_duplicate(gcptr P)
{
    size_t size = stmgc_size(P);
    gcptr L = allocate_nursery(size, -1);
    if (L == NULL)
        return stmgc_duplicate_old(P);

    memcpy(L, P, size);
    L->h_tid &= ~GCFLAG_OLD;
    L->h_tid &= ~GCFLAG_HAS_ID;

    return L;
}

gcptr stmgc_duplicate_old(gcptr P)
{
    size_t size = stmgc_size(P);
    gcptr L = (gcptr)stmgcpage_malloc(size);
    memcpy(L, P, size);
    L->h_tid |= GCFLAG_OLD;

    return L;
}

/************************************************************/

static inline gcptr create_old_object_copy(gcptr obj)
{
    assert(!(obj->h_tid & GCFLAG_PUBLIC));
    assert(!(obj->h_tid & GCFLAG_NURSERY_MOVED));
    assert(!(obj->h_tid & GCFLAG_VISITED));
    assert(!(obj->h_tid & GCFLAG_WRITE_BARRIER));
    assert(!(obj->h_tid & GCFLAG_PREBUILT_ORIGINAL));
    assert(!(obj->h_tid & GCFLAG_OLD));

    gcptr fresh_old_copy = stmgc_duplicate_old(obj);

    dprintf(("minor: %p is copied to %p\n", obj, fresh_old_copy));
    return fresh_old_copy;
}

static void visit_if_young(gcptr *root)
{
    gcptr obj = *root;
    gcptr fresh_old_copy;
    struct tx_descriptor *d = thread_descriptor;

    if (!stmgc_is_in_nursery(d, obj)) {
        /* not a nursery object */
    }
    else {
        /* it's a nursery object.  Was it already moved? */
        if (UNLIKELY(obj->h_tid & GCFLAG_NURSERY_MOVED)) {
            /* yes.  Such an object can be a public object in the nursery
               too (such objects are always NURSERY_MOVED).  For all cases,
               we can just fix the ref. 
               Can be stolen objects or those we already moved.
            */
            *root = (gcptr)obj->h_revision;
            return;
        }

        if (obj->h_tid & GCFLAG_HAS_ID) {
            /* already has a place to go to */
            gcptr id_obj = (gcptr)obj->h_original;

            stm_copy_to_old_id_copy(obj, id_obj);
            fresh_old_copy = id_obj;
            obj->h_tid &= ~GCFLAG_HAS_ID;
        } 
        else {
            /* make a copy of it outside */
            fresh_old_copy = create_old_object_copy(obj);
        }
        
        obj->h_tid |= GCFLAG_NURSERY_MOVED;
        obj->h_revision = (revision_t)fresh_old_copy;

        /* fix the original reference */
        *root = fresh_old_copy;

        /* add 'fresh_old_copy' to the list of objects to trace */
        assert(!(fresh_old_copy->h_tid & GCFLAG_PUBLIC));
        gcptrlist_insert(&d->old_objects_to_trace, fresh_old_copy);
    }
}

static void mark_young_roots(struct tx_descriptor *d)
{
    /* we walk the shadowstack from the end, replacing any END_MARKER_OFF
       found with END_MARKER_ON.  When we reach an END_MARKER_ON, we know
       that we have already seen the rest of the stack in the previous
       nursery collection, so we stop.
    */
    gcptr *end = *d->shadowstack_end_ref;

    while (1) {
        assert(end > d->shadowstack);
        gcptr item = *--end;

        if (((revision_t)item) & ~((revision_t)END_MARKER_OFF |
                                   (revision_t)END_MARKER_ON)) {
            /* 'item' is a regular, non-null pointer */
            visit_if_young(end);
        }
        else if (item != NULL) {
            if (item == END_MARKER_OFF)
                *end = END_MARKER_ON;
            else {
                assert(item == END_MARKER_ON);
                break;
            }
        }
    }
}

static void mark_private_from_protected(struct tx_descriptor *d)
{
    long i, size = d->private_from_protected.size;
    gcptr *items = d->private_from_protected.items;

    for (i = d->num_private_from_protected_known_old; i < size; i++) {
        assert(items[i]->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED);
        assert(IS_POINTER(items[i]->h_revision));

        visit_if_young(&items[i]);

        stmgc_trace((gcptr)items[i]->h_revision, &visit_if_young);
    }

    d->num_private_from_protected_known_old = size;
}

static void trace_stub(struct tx_descriptor *d, gcptr S)
{
    revision_t w = ACCESS_ONCE(S->h_revision);
    if ((w & 3) != 2) {
        /* P has a ptr in h_revision, but this object is not a stub
           with a protected pointer.  It has likely been the case
           in the past, but someone made even more changes.
           Nothing to do now.
        */
        dprintf(("trace_stub: %p not a stub, ignored\n", S));
        return;
    }

    assert(S->h_tid & GCFLAG_STUB);
    if (STUB_THREAD(S) != d->public_descriptor) {
        /* Bah, it's indeed a stub but for another thread.  Nothing
           to do now.
        */
        dprintf(("trace_stub: %p stub wrong thread, ignored\n", S));
        return;
    }

    /* It's a stub for us.  It cannot be un-stubbed under our
       feet because we hold our own collection_lock.
    */
    gcptr L = (gcptr)(w - 2);
    dprintf(("trace_stub: %p stub -> %p\n", S, L));
    visit_if_young(&L);
    assert(S->h_tid & GCFLAG_STUB);
    S->h_revision = ((revision_t)L) | 2;
}

static void mark_stolen_young_stubs(struct tx_descriptor *d)
{
    long i, size = d->public_descriptor->stolen_young_stubs.size;
    gcptr *items = d->public_descriptor->stolen_young_stubs.items;

    for (i = 0; i < size; i++) {
        trace_stub(d, items[i]);
    }
    gcptrlist_clear(&d->public_descriptor->stolen_young_stubs);
}

static void mark_public_to_young(struct tx_descriptor *d)
{
    /* "public_with_young_copy" lists the public copies that may have
       a more recent (or in-progress) private or protected object that
       is young.  Note that public copies themselves are always old
       (short of a few exceptions that don't end up in this list).

       The list should only contain old public objects, but beyong that,
       be careful and ignore any strange object: it can show up because
       of aborted transactions (and then some different changes).
    */
    long i, size = d->public_with_young_copy.size;
    gcptr *items = d->public_with_young_copy.items;

    for (i = 0; i < size; i++) {
        gcptr P = items[i];
        assert(P->h_tid & GCFLAG_PUBLIC);
        assert(P->h_tid & GCFLAG_OLD);
        assert(P->h_tid & GCFLAG_PUBLIC_TO_PRIVATE);

        revision_t v = ACCESS_ONCE(P->h_revision);
        wlog_t *item;
        G2L_FIND(d->public_to_private, P, item, goto not_in_public_to_private);

        /* found P in 'public_to_private' */

        if (IS_POINTER(v)) {
            /* P is both a key in public_to_private and an outdated copy.
               We are in a case where we know the transaction will not
               be able to commit successfully.
            */
            dprintf(("public_to_young: %p was modified! abort!\n", P));
            item->val = NULL;
            AbortTransactionAfterCollect(d, ABRT_COLLECT_MINOR);
            continue;
        }

        dprintf(("public_to_young: %p -> %p in public_to_private\n",
                 item->addr, item->val));
        assert(_stm_is_private(item->val));
        visit_if_young(&item->val);
        continue;

    not_in_public_to_private:
        if (!IS_POINTER(v)) {
            /* P is neither a key in public_to_private nor outdated.
               It must come from an older transaction that aborted.
               Nothing to do now.
            */
            dprintf(("public_to_young: %p ignored\n", P));
            continue;
        }

        dprintf(("public_to_young: %p -> ", P));
        trace_stub(d, (gcptr)v);
    }

    gcptrlist_clear(&d->public_with_young_copy);
}

static void visit_all_outside_objects(struct tx_descriptor *d)
{
    while (gcptrlist_size(&d->old_objects_to_trace) > 0) {
        gcptr obj = gcptrlist_pop(&d->old_objects_to_trace);

        assert(obj->h_tid & GCFLAG_OLD);
        assert(!(obj->h_tid & GCFLAG_WRITE_BARRIER));

        /* We add the WRITE_BARRIER flag to objects here, but warning:
           we may occasionally see a PUBLIC object --- one that was
           a private/protected object when it was added to
           old_objects_to_trace, and has been stolen.  So we have to
           check and not do any change to the obj->h_tid in that case.
           Otherwise this conflicts with the rule that we may only
           modify obj->h_tid of a public object in order to add
           PUBLIC_TO_PRIVATE.
        */
        if (!(obj->h_tid & GCFLAG_PUBLIC))
            obj->h_tid |= GCFLAG_WRITE_BARRIER;

        stmgc_trace(obj, &visit_if_young);
    }
}

static void fix_list_of_read_objects(struct tx_descriptor *d)
{
    long i, limit = d->num_read_objects_known_old;
    gcptr *items = d->list_of_read_objects.items;
    assert(d->list_of_read_objects.size >= limit);

    if (d->active == 2) {
        /* inevitable transaction: clear the list of read objects */
        gcptrlist_clear(&d->list_of_read_objects);
    }

    for (i = d->list_of_read_objects.size - 1; i >= limit; --i) {
        gcptr obj = items[i];

        if (!stmgc_is_in_nursery(d, obj)) {
            /* non-young or visited young objects are kept */
            continue;
        }
        else if (obj->h_tid & GCFLAG_NURSERY_MOVED) {
            /* visited nursery objects are kept and updated */
            items[i] = (gcptr)obj->h_revision;
            assert(!(items[i]->h_tid & GCFLAG_STUB));
            continue;
        }
        /* Sanity check: a nursery object without the NURSERY_MOVED flag
           is necessarily a private-without-backup object, or a protected
           object; it cannot be a public object. */
        assert(!(obj->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED));
        assert(!(obj->h_tid & GCFLAG_PUBLIC));
        assert(!IS_POINTER(obj->h_revision));
        /* The listed object was not visited.  Unlist it. */
        items[i] = items[--d->list_of_read_objects.size];
    }
    d->num_read_objects_known_old = d->list_of_read_objects.size;
    fxcache_clear(&d->recent_reads_cache);
}

static void setup_minor_collect(struct tx_descriptor *d)
{
    spinlock_acquire(d->public_descriptor->collection_lock, 'M');  /*minor*/
    if (d->public_descriptor->stolen_objects.size != 0)
        stm_normalize_stolen_objects(d);
}

static void teardown_minor_collect(struct tx_descriptor *d)
{
    assert(gcptrlist_size(&d->old_objects_to_trace) == 0);
    assert(gcptrlist_size(&d->public_with_young_copy) == 0);
    assert(gcptrlist_size(&d->young_weakrefs) == 0);
    assert(gcptrlist_size(&d->public_descriptor->stolen_objects) == 0);

    spinlock_release(d->public_descriptor->collection_lock);
}

static void minor_collect(struct tx_descriptor *d)
{
    dprintf(("minor collection [%p to %p]\n",
             d->nursery_base, d->nursery_end));
    assert(!stm_has_got_any_lock(d));

    /* acquire the "collection lock" first */
    setup_minor_collect(d);

    /* first do this, which asserts that some objects are private ---
       which fails if they have already been GCFLAG_NURSERY_MOVED */
    mark_public_to_young(d);

    mark_young_roots(d);

    visit_if_young(d->thread_local_obj_ref);
    visit_if_young(&d->old_thread_local_obj);

    mark_stolen_young_stubs(d);

    mark_private_from_protected(d);

    visit_all_outside_objects(d);

    fix_list_of_read_objects(d);

    /* now all surviving nursery objects have been moved out, and all
       surviving young-but-outside-the-nursery objects have been flagged
       with GCFLAG_OLD
    */
    stm_move_young_weakrefs(d);

    teardown_minor_collect(d);
    assert(!stm_has_got_any_lock(d));

    /* When doing minor collections with the nursery "mostly empty",
       as occurs when other threads force major collections but this
       thread didn't do much at all, then we clear the nursery using
       the system's madvise().  The goal is twofold: first, if this
       thread only uses very small amounts of memory, it avoids doing
       a memset() to clear a complete section after every major GC.
       Second, if the thread is really idle, then its nursery is sent
       back to the system until it's really needed.
    */
    if ((d->nursery_nextlimit - d->nursery_base) < GC_NURSERY / 10) {
        size_t already_cleared = 0;
        if (d->nursery_cleared == NC_ALREADY_CLEARED) {
            already_cleared = d->nursery_end - d->nursery_current;
        }
        stm_clear_large_memory_chunk(d->nursery_base, GC_NURSERY,
                                     already_cleared);
        d->nursery_cleared = NC_ALREADY_CLEARED;
    }
    else {
        d->nursery_cleared = NC_REGULAR;
    }

    /* if in debugging mode, we allocate a different nursery and make
       the old one inaccessible
    */
#if defined(_GC_DEBUG) && _GC_DEBUG >= 2
    if (d->nursery_cleared == NC_ALREADY_CLEARED)
        assert_cleared(d->nursery_base, GC_NURSERY);
    stm_free(d->nursery_base, GC_NURSERY);
    d->nursery_base = stm_malloc(GC_NURSERY);
    d->nursery_end = d->nursery_base + GC_NURSERY;
    dprintf(("minor: nursery moved to [%p to %p]\n", d->nursery_base,
             d->nursery_end));
    if (d->nursery_cleared == NC_ALREADY_CLEARED)
        memset(d->nursery_base, 0, GC_NURSERY);
#endif
    d->nursery_current = d->nursery_base;
    d->nursery_nextlimit = d->nursery_base;

    assert(!minor_collect_anything_to_do(d));
}

void stmgc_minor_collect(void)
{
    struct tx_descriptor *d = thread_descriptor;
    assert(d->active >= 1);
    minor_collect(d);
    AbortNowIfDelayed();
}

void stmgc_minor_collect_no_abort(void)
{
    struct tx_descriptor *d = thread_descriptor;
    minor_collect(d);
}

#ifndef NDEBUG
int minor_collect_anything_to_do(struct tx_descriptor *d)
{
    if (d->nursery_current == d->nursery_base /*&&
        !g2l_any_entry(&d->young_objects_outside_nursery)*/ ) {
        /* there is no young object */
        assert(gcptrlist_size(&d->public_with_young_copy) == 0);
        assert(gcptrlist_size(&d->young_weakrefs) == 0);
        assert(gcptrlist_size(&d->list_of_read_objects) >=
               d->num_read_objects_known_old);
        assert(gcptrlist_size(&d->private_from_protected) >=
               d->num_private_from_protected_known_old);
        d->num_read_objects_known_old =
            gcptrlist_size(&d->list_of_read_objects);
        d->num_private_from_protected_known_old =
            gcptrlist_size(&d->private_from_protected);
        return 0;
    }
    else {
        /* there are young objects */
        return 1;
    }
}
#endif

static gcptr allocate_next_section(size_t allocate_size, revision_t tid)
{
    /* This is called when the next allocation request hits
       'nursery_nextlimit', which points to the next multiple of
       GC_NURSERY_SECTION bytes in the nursery.

       'tid' is the value to store in the h_tid of the result,
       or if it's equal to -1, it means we must not collect.

       First fix 'nursery_current', left to a bogus value by the caller.
    */
    struct tx_descriptor *d = thread_descriptor;
    d->nursery_current -= allocate_size;

    /* Are we asking for a "reasonable" number of bytes, i.e. a value
       at most equal to one section?
    */
    if (allocate_size > GC_NURSERY_SECTION) {
        /* No */
        if (tid == -1)
            return NULL;    /* cannot collect */

        /* Allocate it externally, and make it old */
        gcptr P = stmgcpage_malloc(allocate_size);
        memset(P, 0, allocate_size);
        P->h_tid = tid | GCFLAG_OLD;
        assert(!(P->h_tid & GCFLAG_PUBLIC));
        gcptrlist_insert(&d->old_objects_to_trace, P);
        return P;
    }

    /* Are we at the end of the nursery? */
    if (d->nursery_nextlimit == d->nursery_end ||
        d->nursery_current == d->nursery_end) {   // stmgc_minor_collect_soon()
        /* Yes */
        if (tid == -1)
            return NULL;    /* cannot collect */

        /* Start a minor collection
         */
        stmgc_minor_collect();
        stmgcpage_possibly_major_collect(0);

        assert(d->nursery_current == d->nursery_base);
        assert(d->nursery_nextlimit == d->nursery_base);
    }

    /* Clear the next section */
    if (d->nursery_cleared != NC_ALREADY_CLEARED)
        memset(d->nursery_nextlimit, 0, GC_NURSERY_SECTION);
    d->nursery_nextlimit += GC_NURSERY_SECTION;

    /* Return the object from there */
    gcptr P = (gcptr)d->nursery_current;
    d->nursery_current += allocate_size;
    assert(d->nursery_current <= d->nursery_nextlimit);

    P->h_tid = tid;
    assert_cleared(((char *)P) + sizeof(revision_t),
                   allocate_size - sizeof(revision_t));
    return P;
}
