/* Imported by rpython/translator/stm/import_stmgc.py */
#include "stmimpl.h"

#define WEAKREF_PTR(wr, sz)  (*(gcptr *)(((char *)(wr)) + (sz) - WORD))


gcptr stm_weakref_allocate(size_t size, unsigned long tid, gcptr obj)
{
    stm_push_root(obj);
    gcptr weakref = stm_allocate_immutable(size, tid);
    obj = stm_pop_root();
    assert(!(weakref->h_tid & GCFLAG_OLD));   /* 'size' too big? */
    assert(stmgc_size(weakref) == size);
    WEAKREF_PTR(weakref, size) = obj;
    gcptrlist_insert(&thread_descriptor->young_weakrefs, weakref);
    dprintf(("alloc weakref %p -> %p\n", weakref, obj));
    return weakref;
}


/***** Minor collection *****/

void stm_move_young_weakrefs(struct tx_descriptor *d)
{
    /* The code relies on the fact that no weakref can be an old object
       weakly pointing to a young object.  Indeed, weakrefs are immutable
       so they cannot point to an object that was created after it.
    */
    while (gcptrlist_size(&d->young_weakrefs) > 0) {
        gcptr weakref = gcptrlist_pop(&d->young_weakrefs);
        if (!(weakref->h_tid & GCFLAG_NURSERY_MOVED))
            continue;   /* the weakref itself dies */

        weakref = (gcptr)weakref->h_revision;
        size_t size = stmgc_size(weakref);
        gcptr pointing_to = WEAKREF_PTR(weakref, size);
        assert(pointing_to != NULL);

        if (stmgc_is_in_nursery(d, pointing_to)) {
            if (pointing_to->h_tid & GCFLAG_NURSERY_MOVED) {
                dprintf(("weakref ptr moved %p->%p\n", 
                         WEAKREF_PTR(weakref, size),
                         (gcptr)pointing_to->h_revision));
                WEAKREF_PTR(weakref, size) = (gcptr)pointing_to->h_revision;
            }
            else {
                dprintf(("weakref lost ptr %p\n", WEAKREF_PTR(weakref, size)));
                WEAKREF_PTR(weakref, size) = NULL;
                continue;   /* no need to remember this weakref any longer */
            }
        }
        else {
            /*  # see test_weakref_to_prebuilt: it's not useful to put
                # weakrefs into 'old_objects_with_weakrefs' if they point
                # to a prebuilt object (they are immortal).  If moreover
                # the 'pointing_to' prebuilt object still has the
                # GCFLAG_NO_HEAP_PTRS flag, then it's even wrong, because
                # 'pointing_to' will not get the GCFLAG_VISITED during
                # the next major collection.  Solve this by not registering
                # the weakref into 'old_objects_with_weakrefs'.
            */
        }
        gcptrlist_insert(&d->public_descriptor->old_weakrefs, weakref);
    }
}


/***** Major collection *****/

static _Bool is_partially_visited(gcptr obj)
{
    /* Based on gcpage.c:visit().  Check the code here if we simplify
       visit().  Returns True or False depending on whether we find any
       version of 'obj' to be VISITED or not.
    */
 restart:
    if (obj->h_tid & GCFLAG_VISITED)
        return 1;

    if (obj->h_revision & 1) {
        assert(!(obj->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED));
        assert(!(obj->h_tid & GCFLAG_STUB));
        return 0;
    }
    else if (obj->h_tid & GCFLAG_PUBLIC) {
        /* h_revision is a ptr: we have a more recent version */
        if (!(obj->h_revision & 2)) {
            /* go visit the more recent version */
            obj = (gcptr)obj->h_revision;
        }
        else {
            /* it's a stub */
            assert(obj->h_tid & GCFLAG_STUB);
            obj = (gcptr)(obj->h_revision - 2);
        }
        goto restart;
    }
    else {
        assert(obj->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED);
        gcptr B = (gcptr)obj->h_revision;
        assert(B->h_tid & (GCFLAG_PUBLIC | GCFLAG_BACKUP_COPY));
        if (B->h_tid & GCFLAG_VISITED)
            return 1;
        assert(!(obj->h_tid & GCFLAG_STUB));
        assert(!(B->h_tid & GCFLAG_STUB));

        if (IS_POINTER(B->h_revision)) {
            assert(B->h_tid & GCFLAG_PUBLIC);
            assert(!(B->h_tid & GCFLAG_BACKUP_COPY));
            assert(!(B->h_revision & 2));

            obj = (gcptr)B->h_revision;
            goto restart;
        }
    }
    return 0;
}

static void visit_old_weakrefs(struct tx_public_descriptor *gcp)
{
    /* Note: it's possible that a weakref points to a public stub to a
       protected object, and only the protected object was marked as
       VISITED so far.  In this case, this function needs to mark the
       public stub as VISITED too.
    */
    long i, size = gcp->old_weakrefs.size;
    gcptr *items = gcp->old_weakrefs.items;

    for (i = 0; i < size; i++) {
        gcptr weakref = items[i];

        /* weakrefs are immutable: during a major collection, they
           cannot be in the nursery, and so there should be only one
           version of each weakref object.  XXX relying on this is
           a bit fragile, but simplifies things a lot... */
        assert(weakref->h_revision & 1);

        if (!(weakref->h_tid & GCFLAG_VISITED)) {
            /* the weakref itself dies */
        }
        else {
            size_t size = stmgc_size(weakref);
            gcptr pointing_to = WEAKREF_PTR(weakref, size);
            assert(pointing_to != NULL);
            if (is_partially_visited(pointing_to)) {
                pointing_to = stmgcpage_visit(pointing_to);
                dprintf(("mweakref ptr moved %p->%p\n",
                         WEAKREF_PTR(weakref, size),
                         pointing_to));

                assert(pointing_to->h_tid & GCFLAG_VISITED);
                WEAKREF_PTR(weakref, size) = pointing_to;
            }
            else {
                /* the weakref appears to be pointing to a dying object,
                   but we don't know for sure now.  Clearing it is left
                   to clean_old_weakrefs(). */
            }
        }
    }
}

static void clean_old_weakrefs(struct tx_public_descriptor *gcp)
{
    long i, size = gcp->old_weakrefs.size;
    gcptr *items = gcp->old_weakrefs.items;

    for (i = size - 1; i >= 0; i--) {
        gcptr weakref = items[i];
        assert(weakref->h_revision & 1);
        if (weakref->h_tid & GCFLAG_VISITED) {
            size_t size = stmgc_size(weakref);
            gcptr pointing_to = WEAKREF_PTR(weakref, size);
            if (pointing_to->h_tid & GCFLAG_VISITED) {
                continue;   /* the target stays alive, the weakref remains */
            }
            dprintf(("mweakref lost ptr %p\n", WEAKREF_PTR(weakref, size)));
            WEAKREF_PTR(weakref, size) = NULL;  /* the target dies */
        }
        /* remove this weakref from the list */
        items[i] = items[--gcp->old_weakrefs.size];
    }
    gcptrlist_compress(&gcp->old_weakrefs);
}

static void for_each_public_descriptor(
                                  void visit(struct tx_public_descriptor *)) {
    struct tx_descriptor *d;
    for (d = stm_tx_head; d; d = d->tx_next)
        visit(d->public_descriptor);

    struct tx_public_descriptor *gcp;
    revision_t index = -1;
    while ((gcp = stm_get_free_public_descriptor(&index)) != NULL)
        visit(gcp);
}

void stm_visit_old_weakrefs(void)
{
    /* Figure out which weakrefs survive, which possibly
       adds more objects to 'objects_to_trace'.
    */
    for_each_public_descriptor(visit_old_weakrefs);
}

void stm_clean_old_weakrefs(void)
{
    /* Clean up the non-surviving weakrefs
     */
    for_each_public_descriptor(clean_old_weakrefs);
}
