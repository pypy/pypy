/* Imported by rpython/translator/stm/import_stmgc.py */
#include "stmimpl.h"


gcptr stm_weakref_allocate(size_t size, unsigned long tid, gcptr obj)
{
    stm_push_root(obj);
    gcptr weakref = stm_allocate_immutable(size, tid);
    obj = stm_pop_root();
    weakref->h_tid |= GCFLAG_WEAKREF;
    assert(!(weakref->h_tid & GCFLAG_OLD));   /* 'size' too big? */
    assert(stmgc_size(weakref) == size);
    *WEAKREF_PTR(weakref, size) = obj;
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
        if (!(weakref->h_tid & GCFLAG_MOVED))
            continue;   /* the weakref itself dies */

        weakref = (gcptr)weakref->h_revision;
        assert(weakref->h_tid & GCFLAG_OLD);
        assert(!IS_POINTER(weakref->h_revision));

        size_t size = stmgc_size(weakref);
        gcptr pointing_to = *WEAKREF_PTR(weakref, size);
        assert(pointing_to != NULL);

        if (stmgc_is_in_nursery(d, pointing_to)) {
            if (pointing_to->h_tid & GCFLAG_MOVED) {
                dprintf(("weakref ptr moved %p->%p\n", 
                         *WEAKREF_PTR(weakref, size),
                         (gcptr)pointing_to->h_revision));
                *WEAKREF_PTR(weakref, size) = (gcptr)pointing_to->h_revision;
            }
            else {
                assert(!IS_POINTER(pointing_to->h_revision));
                assert(IMPLIES(!(pointing_to->h_tid & GCFLAG_HAS_ID),
                               pointing_to->h_original == 0));

                dprintf(("weakref lost ptr %p\n", *WEAKREF_PTR(weakref, size)));
                *WEAKREF_PTR(weakref, size) = NULL;
                continue;   /* no need to remember this weakref any longer */
            }
        }
        assert((*WEAKREF_PTR(weakref, size))->h_tid & GCFLAG_OLD);
        /* in case we now point to a stub because the weakref got stolen,
           simply keep by inserting into old_weakrefs */

        gcptrlist_insert(&d->public_descriptor->old_weakrefs, weakref);
    }
}


/***** Major collection *****/

static _Bool is_partially_visited(gcptr obj)
{
    /* Based on gcpage.c:visit_public().  Check the code here if we change
       visit_public().  Returns True or False depending on whether we find any
       version of 'obj' to be MARKED or not.
    */
    assert(IMPLIES(obj->h_tid & GCFLAG_VISITED,
                   obj->h_tid & GCFLAG_MARKED));
    if (obj->h_tid & GCFLAG_MARKED)
        return 1;

    /* if (!(obj->h_tid & GCFLAG_PUBLIC)) */
    /*     return 0; */
    assert(!(obj->h_tid & GCFLAG_PREBUILT_ORIGINAL));
    if (obj->h_original != 0) {
        gcptr original = (gcptr)obj->h_original;
        assert(IMPLIES(original->h_tid & GCFLAG_VISITED,
                       original->h_tid & GCFLAG_MARKED));
        if (original->h_tid & GCFLAG_MARKED)
            return 1;
    }
    return 0;
}

static void update_old_weakrefs_list(struct tx_public_descriptor *gcp)
{
    long i, size = gcp->old_weakrefs.size;
    gcptr *items = gcp->old_weakrefs.items;

    for (i = 0; i < size; i++) {
        gcptr weakref = items[i];

        /* if a weakref moved, update its position in the list */
        if (weakref->h_tid & GCFLAG_MOVED) {
            items[i] = (gcptr)weakref->h_original;
        }
    }
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

        if (!(weakref->h_tid & GCFLAG_VISITED)) {
            /* the weakref itself dies */
        }
        else {
            /* the weakref belongs to our thread, therefore we should
               always see the most current revision here: */
            assert(weakref->h_revision & 1);

            size_t size = stmgc_size(weakref);
            gcptr pointing_to = *WEAKREF_PTR(weakref, size);
            assert(pointing_to != NULL);
            if (is_partially_visited(pointing_to)) {
                pointing_to = stmgcpage_visit(pointing_to);
                dprintf(("mweakref ptr moved %p->%p\n",
                         *WEAKREF_PTR(weakref, size),
                         pointing_to));

                assert(pointing_to->h_tid & GCFLAG_VISITED);
                *WEAKREF_PTR(weakref, size) = pointing_to;
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
            gcptr pointing_to = *WEAKREF_PTR(weakref, size);
            if (pointing_to->h_tid & GCFLAG_VISITED) {
                continue;   /* the target stays alive, the weakref remains */
            }
            dprintf(("mweakref lost ptr %p\n", *WEAKREF_PTR(weakref, size)));
            *WEAKREF_PTR(weakref, size) = NULL;  /* the target dies */
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

void stm_update_old_weakrefs_lists(void)
{
    /* go over old weakrefs lists and update the list with possibly
       new pointers because of copy_over_original */
    for_each_public_descriptor(update_old_weakrefs_list);
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
