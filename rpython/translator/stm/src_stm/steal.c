/* Imported by rpython/translator/stm/import_stmgc.py */
#include "stmimpl.h"


gcptr stm_stub_malloc(struct tx_public_descriptor *pd, size_t minsize)
{
    assert(pd->collection_lock != 0);
    if (minsize < sizeof(struct stm_stub_s))
        minsize = sizeof(struct stm_stub_s);

    gcptr p = stmgcpage_malloc(minsize);
    STUB_THREAD(p) = pd;
    return p;
}


struct tx_steal_data {
    struct tx_public_descriptor *foreign_pd;
    struct G2L all_stubs;   /* { protected: public_stub } */
};
static __thread struct tx_steal_data *steal_data;


static void replace_ptr_to_protected_with_stub(gcptr *pobj)
{
    gcptr stub, obj = *pobj;
    if (obj == NULL || (obj->h_tid & (GCFLAG_PUBLIC | GCFLAG_OLD)) ==
                                     (GCFLAG_PUBLIC | GCFLAG_OLD))
        return;

    /* if ((obj->h_tid & GCFLAG_PUBLIC) && (obj->h_tid & GCFLAG_MOVED)) { */
    /*     /\* young stolen public, replace with stolen old copy */
    /*        All references in this old object should be stubbed already */
    /*        by stealing.*\/ */
    /*     assert(IS_POINTER(obj->h_revision)); */
    /*     stub = (gcptr)obj->h_revision; */
    /*     assert(stub->h_tid & GCFLAG_OLD); */
    /*     assert(stub->h_tid & GCFLAG_PUBLIC); */
    /*     goto done; */
    /* } */

    /* we use 'all_stubs', a dictionary, in order to try to avoid
       duplicate stubs for the same object.  XXX maybe it would be
       better to use a fast approximative cache that stays around for
       several stealings. */
    struct tx_steal_data *sd = steal_data;
    wlog_t *item;
    G2L_FIND(sd->all_stubs, obj, item, goto not_found);

    /* found already */
    stub = item->val;
    assert(stub->h_tid & GCFLAG_STUB);
    assert(stub->h_revision == (((revision_t)obj) | 2));
    goto done;

 not_found:;
    size_t size = 0;
    if (!obj->h_original && !(obj->h_tid & GCFLAG_OLD)) {
        /* There shouldn't be a public, young object without
           a h_original. But there can be priv/protected ones.
           We have a young protected copy without an h_original
           The stub we allocate will be the h_original, but
           it must be big enough to be copied over by a major
           collection later. */
        assert(!(obj->h_tid & GCFLAG_PUBLIC));
        
        size = stmgc_size(obj);
    }
    stub = stm_stub_malloc(sd->foreign_pd, size);
    stub->h_tid = (obj->h_tid & STM_USER_TID_MASK) | GCFLAG_PUBLIC
                                                   | GCFLAG_STUB
                                                   | GCFLAG_OLD;
    if (size == 0)
        stub->h_tid |= GCFLAG_SMALLSTUB;
    stub->h_revision = ((revision_t)obj) | 2;
    if (obj->h_original) {
        stub->h_original = obj->h_original;
    }
    else if (obj->h_tid & GCFLAG_OLD) {
        stub->h_original = (revision_t)obj;
    }
    else {
        /* this is the big-stub case described above */
        obj->h_original = (revision_t)stub; 
        stub->h_original = 0;   /* stub_malloc does not set to 0... */
        if (obj->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED) {
            ((gcptr)obj->h_revision)->h_original = (revision_t)stub;
        }
    }

    g2l_insert(&sd->all_stubs, obj, stub);

    if (!(obj->h_tid & GCFLAG_OLD))
        gcptrlist_insert(&sd->foreign_pd->stolen_young_stubs, stub);

 done:
    *pobj = stub;
    dprintf(("  stolen: fixing *%p: %p -> %p\n", pobj, obj, stub));
}

void stm_steal_stub(gcptr P)
{
    struct tx_public_descriptor *foreign_pd = STUB_THREAD(P);
    /* A note about dead threads: 'foreign_pd' might belong to a thread
     * that finished and is no longer around.  In this case, note that
     * this function will not add anything to 'foreign_pd->stolen_objects':
     * 
     * 1. the dead thread is not running a transaction, so there are no
     *    private objects (so no PRIVATE_FROM_PROTECTED)
     *
     * 2. the dead thread has no nursery, so all of its objects are old
     */

    spinlock_acquire(foreign_pd->collection_lock, 'S');   /*stealing*/

    revision_t v = ACCESS_ONCE(P->h_revision);
    if ((v & 3) != 2)
        goto done;     /* un-stubbed while we waited for the lock */

    gcptr L = (gcptr)(v - 2);

    /* L might be a private_from_protected, or just a protected copy.
       To know which case it is, read GCFLAG_PRIVATE_FROM_PROTECTED.
    */
    if (L->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED) {
        assert(!(L->h_tid & GCFLAG_IMMUTABLE));
        gcptr B = (gcptr)L->h_revision;     /* the backup copy */
        
        /* On young objects here, h_original is always set
         and never GCFLAG_HAS_ID. This is because a stealing
         thread can only reach a priv_from_prot object through
         public old stubs/objects that serve as originals if
         needed.
         If h_original is set, then it is already set in the
         backup, too.
        */
        assert(!(L->h_tid & GCFLAG_HAS_ID));
        assert(IMPLIES(!(L->h_tid & GCFLAG_OLD), L->h_original));
        assert(IMPLIES(L->h_tid & GCFLAG_OLD,
                       (B->h_original == (revision_t)L) 
                       || (B->h_original == L->h_original)));
        if (!L->h_original && L->h_tid & GCFLAG_OLD) {
            /* If old, L must be the original */
            B->h_original = (revision_t)L;
        }

        /* B is now a backup copy, i.e. a protected object, and we own
           the foreign thread's collection_lock, so we can read/write the
           flags.  B is old, like all backup copies.
        */
        assert(B->h_tid & GCFLAG_OLD);
        B->h_tid &= ~GCFLAG_BACKUP_COPY;

        if (B->h_tid & GCFLAG_PUBLIC_TO_PRIVATE) {
            /* already stolen */
            assert(B->h_tid & GCFLAG_PUBLIC);
            dprintf(("already stolen: %p -> %p <-> %p\n", P, L, B));
            L = B;
            goto already_stolen;
        }

        B->h_tid |= GCFLAG_PUBLIC_TO_PRIVATE;
        /* add {B: L} in 'public_to_private', but lazily, because we
           don't want to walk over the feet of the foreign thread
        */
        gcptrlist_insert2(&foreign_pd->stolen_objects, B, L);
        dprintf(("stolen: %p -> %p <-> %p\n", P, L, B));
        L = B;
    }
    else {
        if (L->h_tid & GCFLAG_PUBLIC) {
            /* already stolen */
            dprintf(("already stolen: %p -> %p\n", P, L));

            /* note that we should follow h_revision at least one more
               step: in the case where L is public but young (and then
               has GCFLAG_MOVED).  Don't do it generally!  L might be
               a stub again. */
            if (L->h_tid & GCFLAG_MOVED) {
                v = ACCESS_ONCE(L->h_revision);
                assert(IS_POINTER(v));
                L = (gcptr)v;
                dprintf(("\t---> %p\n", L));
            }
            goto already_stolen;
        }

        dprintf(("stolen: %p -> %p\n", P, L));

        
        if (!(L->h_tid & GCFLAG_OLD)) { 
            gcptr O;
            
            if (L->h_tid & GCFLAG_HAS_ID) {
                /* use id-copy for us */
                O = (gcptr)L->h_original;
                assert(O != L);
                L->h_tid &= ~GCFLAG_HAS_ID;
                stm_copy_to_old_id_copy(L, O);
                O->h_original = 0;
            } else {
                /* Copy the object out of the other thread's nursery, 
                   if needed */
                O = stmgc_duplicate_old(L);
                assert(O != L);

                /* young and without original? */
                if (!(L->h_original))
                    L->h_original = (revision_t)O;
            }
            L->h_revision = (revision_t)O;

            L->h_tid |= GCFLAG_PUBLIC | GCFLAG_MOVED;
            /* subtle: we need to remove L from the fxcache of the target
               thread, otherwise its read barrier might not trigger on it.
               It is mostly fine because it is anyway identical to O.  But
               the issue is if the target thread adds a public_to_private
               off O later: the write barrier will miss it if it only sees
               L. */
            gcptrlist_insert2(&foreign_pd->stolen_objects, L, NULL);
            L = O;
            dprintf(("\t---> %p\n", L));
        }

        assert(L->h_tid & GCFLAG_OLD);
    }

    /* Here L is a protected (or backup) copy, and we own the foreign
       thread's collection_lock, so we can read/write the flags.  Change
       it from protected to public.
    */
    assert(!(L->h_tid & GCFLAG_PUBLIC));
    L->h_tid |= GCFLAG_PUBLIC;

    /* Note that all protected or backup copies have a h_revision that
       is odd.
    */
    assert(L->h_revision & 1);

    /* At this point, the object can only be seen by its owning foreign
       thread and by us.  No 3rd thread can see it as long as we own
       the foreign thread's collection_lock.  For the foreign thread,
       it might suddenly see the GCFLAG_PUBLIC being added to L
       (but it may not do any change to the flags itself, because
       it cannot grab its own collection_lock).  L->h_revision is an
       odd number that is also valid on a public up-to-date object.
    */

    /* Fix the content of the object: we need to change all pointers
       that reference protected copies into pointers that reference
       stub copies.
    */
    struct tx_steal_data sd;
    sd.foreign_pd = foreign_pd;
    memset(&sd.all_stubs, 0, sizeof(sd.all_stubs));
    steal_data = &sd;
    stmgc_trace(L, &replace_ptr_to_protected_with_stub);
    if (L->h_tid & GCFLAG_WEAKREF)
        replace_ptr_to_protected_with_stub(WEAKREF_PTR(L, stmgc_size(L)));
    g2l_delete_not_used_any_more(&sd.all_stubs);

    /* If another thread (the foreign or a 3rd party) does a read
       barrier from P, it must only reach L if all writes to L are
       visible; i.e. it must not see P->h_revision => L that still
       doesn't have the GCFLAG_PUBLIC.  So we need a CPU write
       barrier here.
    */
    smp_wmb();

 already_stolen:
    assert(L->h_tid & GCFLAG_OLD);

    /* update the original P->h_revision to point directly to L */
    P->h_revision = (revision_t)L;

 done:
    spinlock_release(foreign_pd->collection_lock);
}

void stm_normalize_stolen_objects(struct tx_descriptor *d)
{
    long i, size = d->public_descriptor->stolen_objects.size;
    gcptr *items = d->public_descriptor->stolen_objects.items;

    for (i = 0; i < size; i += 2) {
        gcptr B = items[i];
        assert(!(B->h_tid & GCFLAG_BACKUP_COPY));  /* already removed */
        assert(B->h_tid & GCFLAG_PUBLIC);

        /* to be on the safe side --- but actually needed, see the
           gcptrlist_insert2(L, NULL) above */
        fxcache_remove(&d->recent_reads_cache, B);

        gcptr L = items[i + 1];
        if (L == NULL)
            continue;
        assert(L->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED);
        assert(IS_POINTER(L->h_revision));

        assert(B->h_tid & GCFLAG_PUBLIC_TO_PRIVATE);
        g2l_insert(&d->public_to_private, B, L);

        /* this is definitely needed: all keys in public_to_private
           must appear in list_of_read_objects */
        dprintf(("n.readobj: %p -> %p\n", B, L));
        assert(!(B->h_tid & GCFLAG_STUB));
        gcptrlist_insert(&d->list_of_read_objects, B);

        /* must also list it here, in case the next minor collect moves it */
        if (!(L->h_tid & GCFLAG_OLD))
            gcptrlist_insert(&d->public_with_young_copy, B);
    }
    gcptrlist_clear(&d->public_descriptor->stolen_objects);
}

gcptr _stm_find_stolen_objects(struct tx_descriptor *d, gcptr obj)
{
    /* read-only, for debugging */
    long i, size = d->public_descriptor->stolen_objects.size;
    gcptr *items = d->public_descriptor->stolen_objects.items;

    for (i = 0; i < size; i += 2) {
        gcptr B = items[i];
        gcptr L = items[i + 1];

        assert(L->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED);
        if (B == obj)
            return L;
    }
    return NULL;
}
