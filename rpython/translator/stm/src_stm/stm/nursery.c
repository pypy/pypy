/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif

/************************************************************/

#define NURSERY_START         (FIRST_NURSERY_PAGE * 4096UL)
#define NURSERY_SIZE          (NB_NURSERY_PAGES * 4096UL)
#define NURSERY_END           (NURSERY_START + NURSERY_SIZE)

static uintptr_t _stm_nursery_start;


/************************************************************/

static void setup_nursery(void)
{
    assert(_STM_FAST_ALLOC <= NURSERY_SIZE);
    _stm_nursery_start = NURSERY_START;

    long i;
    for (i = 0; i < NB_SEGMENTS; i++) {
        get_segment(i)->nursery_current = (stm_char *)NURSERY_START;
        get_segment(i)->nursery_end = NURSERY_END;
    }
}

static inline bool _is_in_nursery(object_t *obj)
{
    assert((uintptr_t)obj >= NURSERY_START);
    return (uintptr_t)obj < NURSERY_END;
}

static inline bool _is_young(object_t *obj)
{
    return (_is_in_nursery(obj) ||
        tree_contains(STM_PSEGMENT->young_outside_nursery, (uintptr_t)obj));
}

long stm_can_move(object_t *obj)
{
    /* 'long' return value to avoid using 'bool' in the public interface */
    return _is_in_nursery(obj);
}


/************************************************************/
static object_t *find_existing_shadow(object_t *obj);
#define GCWORD_MOVED  ((object_t *) -1)
#define FLAG_SYNC_LARGE       0x01


static void minor_trace_if_young(object_t **pobj)
{
    /* takes a normal pointer to a thread-local pointer to an object */
    object_t *obj = *pobj;
    uintptr_t nobj_sync_now;
    object_t *nobj;
    char *realobj;
    size_t size;

    if (obj == NULL)
        return;
    assert((uintptr_t)obj < NB_PAGES * 4096UL);

    if (_is_in_nursery(obj)) {
        /* If the object was already seen here, its first word was set
           to GCWORD_MOVED.  In that case, the forwarding location, i.e.
           where the object moved to, is stored in the second word in 'obj'. */
        object_t *TLPREFIX *pforwarded_array = (object_t *TLPREFIX *)obj;

        if (obj->stm_flags & GCFLAG_HAS_SHADOW) {
            /* ^^ the single check above detects both already-moved objects
               and objects with HAS_SHADOW.  This is because GCWORD_MOVED
               overrides completely the stm_flags field with 1's bits. */

            if (LIKELY(pforwarded_array[0] == GCWORD_MOVED)) {
                *pobj = pforwarded_array[1];    /* already moved */
                return;
            }

            /* really has a shadow */
            nobj = find_existing_shadow(obj);
            obj->stm_flags &= ~GCFLAG_HAS_SHADOW;
            realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
            size = stmcb_size_rounded_up((struct object_s *)realobj);

            dprintf(("has_shadow(%p): %p, sz:%lu\n",
                     obj, nobj, size));
            goto copy_large_object;
        }

        realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
        size = stmcb_size_rounded_up((struct object_s *)realobj);

        if (size > GC_LAST_SMALL_SIZE) {
            /* case 1: object is not small enough.
               Ask gcpage.c for an allocation via largemalloc. */
            nobj = (object_t *)allocate_outside_nursery_large(size);
        }
        else {
            /* case "small enough" */
            nobj = (object_t *)allocate_outside_nursery_small(size);
        }

        dprintf(("move %p -> %p\n", obj, nobj));

        /* copy the object */
    copy_large_object:;
        char *realnobj = REAL_ADDRESS(STM_SEGMENT->segment_base, nobj);
        memcpy(realnobj, realobj, size);

        nobj_sync_now = ((uintptr_t)nobj) | FLAG_SYNC_LARGE;

        pforwarded_array[0] = GCWORD_MOVED;
        pforwarded_array[1] = nobj;
        *pobj = nobj;
    }
    else {
        /* The object was not in the nursery at all */
        if (LIKELY(!tree_contains(STM_PSEGMENT->young_outside_nursery,
                                  (uintptr_t)obj)))
            return;   /* common case: it was an old object, nothing to do */

        /* a young object outside the nursery */
        nobj = obj;
        tree_delete_item(STM_PSEGMENT->young_outside_nursery, (uintptr_t)nobj);
        nobj_sync_now = ((uintptr_t)nobj) | FLAG_SYNC_LARGE;
    }

    /* if this is not during commit, we will add them to the new_objects
       list and push them to other segments on commit. Thus we can add
       the WB_EXECUTED flag so that they don't end up in modified_old_objects */
    assert(!(nobj->stm_flags & GCFLAG_WB_EXECUTED));
    if (!STM_PSEGMENT->minor_collect_will_commit_now) {
        nobj->stm_flags |= GCFLAG_WB_EXECUTED;
    }

    /* Must trace the object later */
    LIST_APPEND(STM_PSEGMENT->objects_pointing_to_nursery, nobj_sync_now);
}


static void collect_roots_in_nursery(void)
{
    stm_thread_local_t *tl = STM_SEGMENT->running_thread;
    struct stm_shadowentry_s *current = tl->shadowstack;
    struct stm_shadowentry_s *finalbase = tl->shadowstack_base;
    struct stm_shadowentry_s *ssbase;
    ssbase = (struct stm_shadowentry_s *)tl->rjthread.moved_off_ssbase;
    if (ssbase == NULL)
        ssbase = finalbase;
    else
        assert(finalbase <= ssbase && ssbase <= current);

    while (current > ssbase) {
        --current;
        uintptr_t x = (uintptr_t)current->ss;

        if ((x & 3) == 0) {
            /* the stack entry is a regular pointer (possibly NULL) */
            minor_trace_if_young(&current->ss);
        }
        else {
            /* it is an odd-valued marker, ignore */
        }
    }

    minor_trace_if_young(&tl->thread_local_obj);
}


static inline void _collect_now(object_t *obj)
{
    assert(!_is_young(obj));

    dprintf(("_collect_now: %p\n", obj));

    assert(!(obj->stm_flags & GCFLAG_WRITE_BARRIER));

    char *realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    stmcb_trace((struct object_s *)realobj, &minor_trace_if_young);

    obj->stm_flags |= GCFLAG_WRITE_BARRIER;
}


static void collect_oldrefs_to_nursery(void)
{
    dprintf(("collect_oldrefs_to_nursery\n"));
    struct list_s *lst = STM_PSEGMENT->objects_pointing_to_nursery;

    while (!list_is_empty(lst)) {
        uintptr_t obj_sync_now = list_pop_item(lst);
        object_t *obj = (object_t *)(obj_sync_now & ~FLAG_SYNC_LARGE);

        assert(!_is_in_nursery(obj));

        _collect_now(obj);

        if (obj_sync_now & FLAG_SYNC_LARGE) {
            /* this is a newly allocated obj in this transaction. We must
               either synchronize the object to other segments now, or
               add the object to new_objects list */
            if (STM_PSEGMENT->minor_collect_will_commit_now) {
                acquire_privatization_lock(STM_SEGMENT->segment_num);
                synchronize_object_enqueue(obj);
                release_privatization_lock(STM_SEGMENT->segment_num);
            } else {
                LIST_APPEND(STM_PSEGMENT->new_objects, obj);
            }
        }

        /* the list could have moved while appending */
        lst = STM_PSEGMENT->objects_pointing_to_nursery;
    }

    /* flush all new objects to other segments now */
    if (STM_PSEGMENT->minor_collect_will_commit_now) {
        acquire_privatization_lock(STM_SEGMENT->segment_num);
        synchronize_objects_flush();
        release_privatization_lock(STM_SEGMENT->segment_num);
    } else {
        /* nothing in the queue when not committing */
        assert(STM_PSEGMENT->sq_len == 0);
    }
}


static size_t throw_away_nursery(struct stm_priv_segment_info_s *pseg)
{
#pragma push_macro("STM_PSEGMENT")
#pragma push_macro("STM_SEGMENT")
#undef STM_PSEGMENT
#undef STM_SEGMENT
    dprintf(("throw_away_nursery\n"));
    /* reset the nursery by zeroing it */
    size_t nursery_used;
    char *realnursery;

    realnursery = REAL_ADDRESS(pseg->pub.segment_base, _stm_nursery_start);
    nursery_used = pseg->pub.nursery_current - (stm_char *)_stm_nursery_start;
    if (nursery_used > NB_NURSERY_PAGES * 4096) {
        /* possible in rare cases when the program artificially advances
           its own nursery_current */
        nursery_used = NB_NURSERY_PAGES * 4096;
    }
    OPT_ASSERT((nursery_used & 7) == 0);
    memset(realnursery, 0, nursery_used);

    /* assert that the rest of the nursery still contains only zeroes */
    assert_memset_zero(realnursery + nursery_used,
                       (NURSERY_END - _stm_nursery_start) - nursery_used);

    pseg->pub.nursery_current = (stm_char *)_stm_nursery_start;

    /* free any object left from 'young_outside_nursery' */
    if (!tree_is_cleared(pseg->young_outside_nursery)) {
        wlog_t *item;

        if (!tree_is_empty(pseg->young_outside_nursery)) {
            /* tree may still be empty even if not cleared */
            TREE_LOOP_FORWARD(pseg->young_outside_nursery, item) {
                object_t *obj = (object_t*)item->addr;
                assert(!_is_in_nursery(obj));

                /* mark slot as unread (it can only have the read marker
                   in this segment) */
                *((char *)(pseg->pub.segment_base + (((uintptr_t)obj) >> 4))) = 0;

                _stm_large_free(stm_object_pages + item->addr);
            } TREE_LOOP_END;
        }

        tree_clear(pseg->young_outside_nursery);
    }

    tree_clear(pseg->nursery_objects_shadows);

    return nursery_used;
#pragma pop_macro("STM_SEGMENT")
#pragma pop_macro("STM_PSEGMENT")
}

#define MINOR_NOTHING_TO_DO(pseg)                                       \
    ((pseg)->pub.nursery_current == (stm_char *)_stm_nursery_start &&   \
     tree_is_cleared((pseg)->young_outside_nursery))


static void _do_minor_collection(bool commit)
{
    dprintf(("minor_collection commit=%d\n", (int)commit));

    STM_PSEGMENT->minor_collect_will_commit_now = commit;

    collect_roots_in_nursery();

    collect_oldrefs_to_nursery();

    /* now all surviving nursery objects have been moved out */
    acquire_privatization_lock(STM_SEGMENT->segment_num);
    stm_move_young_weakrefs();
    release_privatization_lock(STM_SEGMENT->segment_num);

    assert(list_is_empty(STM_PSEGMENT->objects_pointing_to_nursery));

    throw_away_nursery(get_priv_segment(STM_SEGMENT->segment_num));

    assert(MINOR_NOTHING_TO_DO(STM_PSEGMENT));
}

static void minor_collection(bool commit)
{
    assert(!_has_mutex());

    stm_safe_point();

    _do_minor_collection(commit);
}

void stm_collect(long level)
{
    if (level > 0)
        force_major_collection_request();

    minor_collection(/*commit=*/ false);

#ifdef STM_TESTS
    /* tests don't want aborts in stm_allocate, thus
       we only do major collections if explicitly requested */
    if (level > 0)
        major_collection_if_requested();
#else
    major_collection_if_requested();
#endif
}



/************************************************************/


object_t *_stm_allocate_slowpath(ssize_t size_rounded_up)
{
    /* may collect! */
    STM_SEGMENT->nursery_current -= size_rounded_up;  /* restore correct val */

 restart:
    stm_safe_point();

    OPT_ASSERT(size_rounded_up >= 16);
    OPT_ASSERT((size_rounded_up & 7) == 0);
    OPT_ASSERT(size_rounded_up < _STM_FAST_ALLOC);

    stm_char *p = STM_SEGMENT->nursery_current;
    stm_char *end = p + size_rounded_up;
    if ((uintptr_t)end <= NURSERY_END) {
        STM_SEGMENT->nursery_current = end;
        return (object_t *)p;
    }

    stm_collect(0);
    goto restart;
}

object_t *_stm_allocate_external(ssize_t size_rounded_up)
{
    /* first, force a collection if needed */
    if (is_major_collection_requested()) {
        /* use stm_collect() with level 0: if another thread does a major GC
           in-between, is_major_collection_requested() will become false
           again, and we'll avoid doing yet another one afterwards. */
#ifndef STM_TESTS
        /* during tests, we must not do a major collection during allocation.
           The reason is that it may abort us and tests don't expect it. */
        stm_collect(0);
#endif
    }

    object_t *o = (object_t *)allocate_outside_nursery_large(size_rounded_up);

    tree_insert(STM_PSEGMENT->young_outside_nursery, (uintptr_t)o, 0);

    memset(REAL_ADDRESS(STM_SEGMENT->segment_base, o), 0, size_rounded_up);
    return o;
}


#ifdef STM_TESTS
void _stm_set_nursery_free_count(uint64_t free_count)
{
    assert(free_count <= NURSERY_SIZE);
    assert((free_count & 7) == 0);
    _stm_nursery_start = NURSERY_END - free_count;

    long i;
    for (i = 0; i < NB_SEGMENTS; i++) {
        if ((uintptr_t)get_segment(i)->nursery_current < _stm_nursery_start)
            get_segment(i)->nursery_current = (stm_char *)_stm_nursery_start;
    }
}
#endif

static void assert_memset_zero(void *s, size_t n)
{
#ifndef NDEBUG
    size_t i;
# ifndef STM_TESTS
    if (n > 5000) n = 5000;
# endif
    n /= 8;
    for (i = 0; i < n; i++)
        assert(((uint64_t *)s)[i] == 0);
#endif
}

static void check_nursery_at_transaction_start(void)
{
    assert((uintptr_t)STM_SEGMENT->nursery_current == _stm_nursery_start);
    assert_memset_zero(REAL_ADDRESS(STM_SEGMENT->segment_base,
                                    STM_SEGMENT->nursery_current),
                       NURSERY_END - _stm_nursery_start);
}


static void major_do_validation_and_minor_collections(void)
{
    int original_num = STM_SEGMENT->segment_num;
    long i;

    /* including the sharing seg0 */
    for (i = 0; i < NB_SEGMENTS; i++) {
        set_gs_register(get_segment_base(i));

        if (!_stm_validate()) {
            assert(i != 0);     /* sharing seg0 should never need an abort */

            if (STM_PSEGMENT->transaction_state == TS_NONE) {
                /* we found a segment that has stale read-marker data and thus
                   is in conflict with committed objs. Since it is not running
                   currently, it's fine to ignore it. */
                continue;
            }

            /* tell it to abort when continuing */
            STM_PSEGMENT->pub.nursery_end = NSE_SIGABORT;
            assert(must_abort());

            dprintf(("abort data structures\n"));
            abort_data_structures_from_segment_num(i);
            continue;
        }


        if (MINOR_NOTHING_TO_DO(STM_PSEGMENT))  /*TS_NONE segments have NOTHING_TO_DO*/
            continue;

        assert(STM_PSEGMENT->transaction_state != TS_NONE);
        assert(STM_PSEGMENT->safe_point != SP_RUNNING);
        assert(STM_PSEGMENT->safe_point != SP_NO_TRANSACTION);


        /* Other segments that will abort immediately after resuming: we
           have to ignore them, not try to collect them anyway!
           Collecting might fail due to invalid state.
        */
        if (!must_abort()) {
            _do_minor_collection(/*commit=*/ false);
            assert(MINOR_NOTHING_TO_DO(STM_PSEGMENT));
        }
        else {
            dprintf(("abort data structures\n"));
            abort_data_structures_from_segment_num(i);
        }
    }

    set_gs_register(get_segment_base(original_num));
}


static object_t *allocate_shadow(object_t *obj)
{
    char *realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    size_t size = stmcb_size_rounded_up((struct object_s *)realobj);

    /* always gets outside as a large object for now (XXX?) */
    object_t *nobj = (object_t *)allocate_outside_nursery_large(size);

    /* Initialize the shadow enough to be considered a valid gc object.
       If the original object stays alive at the next minor collection,
       it will anyway be copied over the shadow and overwrite the
       following fields.  But if the object dies, then the shadow will
       stay around and only be freed at the next major collection, at
       which point we want it to look valid (but ready to be freed).

       Here, in the general case, it requires copying the whole object.
       It could be more optimized in special cases like in PyPy, by
       copying only the typeid and (for var-sized objects) the length
       field.  It's probably overkill to add a special stmcb_xxx
       interface just for that.
    */
    char *realnobj = REAL_ADDRESS(STM_SEGMENT->segment_base, nobj);
    memcpy(realnobj, realobj, size);

    obj->stm_flags |= GCFLAG_HAS_SHADOW;

    tree_insert(STM_PSEGMENT->nursery_objects_shadows,
                (uintptr_t)obj, (uintptr_t)nobj);

    dprintf(("allocate_shadow(%p): %p\n", obj, nobj));
    return nobj;
}

static object_t *find_existing_shadow(object_t *obj)
{
    wlog_t *item;

    TREE_FIND(STM_PSEGMENT->nursery_objects_shadows,
              (uintptr_t)obj, item, goto not_found);

    /* The answer is the address of the shadow. */
    return (object_t *)item->val;

 not_found:
    stm_fatalerror("GCFLAG_HAS_SHADOW but no shadow found");
}

static object_t *find_shadow(object_t *obj)
{
    /* The object 'obj' is still in the nursery.  Find or allocate a
        "shadow" object, which is where the object will be moved by the
        next minor collection
    */
    if (obj->stm_flags & GCFLAG_HAS_SHADOW)
        return find_existing_shadow(obj);
    else
        return allocate_shadow(obj);
}
