/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif

/************************************************************/

/* xxx later: divide the nursery into sections, and zero them
   incrementally.  For now we avoid the mess of maintaining a
   description of which parts of the nursery are already zeroed
   and which ones are not (caused by the fact that each
   transaction fills up a different amount).
*/

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
    for (i = 1; i <= NB_SEGMENTS; i++) {
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

static object_t *find_existing_shadow(object_t *obj);


/************************************************************/

#define GCWORD_MOVED  ((object_t *) -1)
#define FLAG_SYNC_LARGE       0x01


static void minor_trace_if_young(object_t **pobj)
{
    /* takes a normal pointer to a thread-local pointer to an object */
    object_t *obj = *pobj;
    object_t *nobj;
    uintptr_t nobj_sync_now;

    if (obj == NULL)
        return;
    assert((uintptr_t)obj < NB_PAGES * 4096UL);

    if (_is_in_nursery(obj)) {
        /* If the object was already seen here, its first word was set
           to GCWORD_MOVED.  In that case, the forwarding location, i.e.
           where the object moved to, is stored in the second word in 'obj'. */
        object_t *TLPREFIX *pforwarded_array = (object_t *TLPREFIX *)obj;
        char *realobj;
        size_t size;

        if (obj->stm_flags & GCFLAG_HAS_SHADOW) {
            /* ^^ the single check above detects both already-moved objects
               and objects with HAS_SHADOW.  This is because GCWORD_MOVED
               overrides completely the stm_flags field with 1's bits. */

            if (LIKELY(pforwarded_array[0] == GCWORD_MOVED)) {
                *pobj = pforwarded_array[1];    /* already moved */
                return;
            }
            else {
                /* really has a shadow */
                nobj = find_existing_shadow(obj);
                obj->stm_flags &= ~GCFLAG_HAS_SHADOW;
                realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
                size = stmcb_size_rounded_up((struct object_s *)realobj);
                goto copy_large_object;
            }
        }
        /* We need to make a copy of this object.  It goes either in
           a largemalloc.c-managed area, or if it's small enough, in
           one of the small uniform pages from gcpage.c.
        */
        realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
        size = stmcb_size_rounded_up((struct object_s *)realobj);

        if (1 /*size >= GC_N_SMALL_REQUESTS*8*/) {

            /* case 1: object is not small enough.
               Ask gcpage.c for an allocation via largemalloc. */
            char *allocated = allocate_outside_nursery_large(size);
            nobj = (object_t *)(allocated - stm_object_pages);

            /* Copy the object */
         copy_large_object:;
            char *realnobj = REAL_ADDRESS(STM_SEGMENT->segment_base, nobj);
            memcpy(realnobj, realobj, size);

            nobj_sync_now = ((uintptr_t)nobj) | FLAG_SYNC_LARGE;
        }
        else {
            /* case "small enough" */
            abort();  //...
        }

        /* Done copying the object. */
        //dprintf(("\t\t\t\t\t%p -> %p\n", obj, nobj));
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

    /* Set the overflow_number if nedeed */
    assert((nobj->stm_flags & -GCFLAG_OVERFLOW_NUMBER_bit0) == 0);
    if (!STM_PSEGMENT->minor_collect_will_commit_now) {
        nobj->stm_flags |= STM_PSEGMENT->overflow_number;
    }

    /* Must trace the object later */
    LIST_APPEND(STM_PSEGMENT->objects_pointing_to_nursery, nobj_sync_now);
}

static void collect_roots_in_nursery(void)
{
    stm_thread_local_t *tl = STM_SEGMENT->running_thread;
    struct stm_shadowentry_s *current = tl->shadowstack;
    struct stm_shadowentry_s *base = tl->shadowstack_base;
    while (1) {
        --current;
        OPT_ASSERT(current >= base);

        uintptr_t x = (uintptr_t)current->ss;

        if ((x & 3) == 0) {
            /* the stack entry is a regular pointer (possibly NULL) */
            minor_trace_if_young(&current->ss);
        }
        else if (x == STM_STACK_MARKER_NEW) {
            /* the marker was not already seen: mark it as seen,
               but continue looking more deeply in the shadowstack */
            current->ss = (object_t *)STM_STACK_MARKER_OLD;
        }
        else if (x == STM_STACK_MARKER_OLD) {
            /* the marker was already seen: we can stop the
               root stack tracing at this point */
            break;
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

    /* We must not have GCFLAG_WRITE_BARRIER so far.  Add it now. */
    assert(!(obj->stm_flags & GCFLAG_WRITE_BARRIER));
    obj->stm_flags |= GCFLAG_WRITE_BARRIER;

    /* Trace the 'obj' to replace pointers to nursery with pointers
       outside the nursery, possibly forcing nursery objects out and
       adding them to 'objects_pointing_to_nursery' as well. */
    char *realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    stmcb_trace((struct object_s *)realobj, &minor_trace_if_young);
}

static void collect_oldrefs_to_nursery(void)
{
    struct list_s *lst = STM_PSEGMENT->objects_pointing_to_nursery;

    while (!list_is_empty(lst)) {
        uintptr_t obj_sync_now = list_pop_item(lst);
        object_t *obj = (object_t *)(obj_sync_now & ~FLAG_SYNC_LARGE);

        _collect_now(obj);

        if (obj_sync_now & FLAG_SYNC_LARGE) {
            /* this was a large object.  We must either synchronize the
               object to other segments now (after we added the
               WRITE_BARRIER flag and traced into it to fix its
               content); or add the object to 'large_overflow_objects'.
            */
            if (STM_PSEGMENT->minor_collect_will_commit_now) {
                synchronize_object_now(obj);
            }
            else
                LIST_APPEND(STM_PSEGMENT->large_overflow_objects, obj);
        }

        /* the list could have moved while appending */
        lst = STM_PSEGMENT->objects_pointing_to_nursery;
    }
}

static void collect_modified_old_objects(void)
{
    LIST_FOREACH_R(STM_PSEGMENT->modified_old_objects, object_t * /*item*/,
                   _collect_now(item));
}

static size_t throw_away_nursery(struct stm_priv_segment_info_s *pseg)
{
    /* reset the nursery by zeroing it */
    size_t nursery_used;
    char *realnursery;

    realnursery = REAL_ADDRESS(pseg->pub.segment_base, _stm_nursery_start);
    nursery_used = pseg->pub.nursery_current - (stm_char *)_stm_nursery_start;
    OPT_ASSERT((nursery_used & 7) == 0);
    memset(realnursery, 0, nursery_used);

    /* assert that the rest of the nursery still contains only zeroes */
    assert_memset_zero(realnursery + nursery_used,
                       (NURSERY_END - _stm_nursery_start) - nursery_used);

    pseg->pub.nursery_current = (stm_char *)_stm_nursery_start;

    /* free any object left from 'young_outside_nursery' */
    if (!tree_is_cleared(pseg->young_outside_nursery)) {
        wlog_t *item;

        TREE_LOOP_FORWARD(*pseg->young_outside_nursery, item) {
            assert(!_is_in_nursery((object_t *)item->addr));
            _stm_large_free(stm_object_pages + item->addr);
        } TREE_LOOP_END;

        tree_clear(pseg->young_outside_nursery);
    }

    tree_clear(pseg->nursery_objects_shadows);
    return nursery_used;
}

#define MINOR_NOTHING_TO_DO(pseg)                                       \
    ((pseg)->pub.nursery_current == (stm_char *)_stm_nursery_start &&   \
     tree_is_cleared((pseg)->young_outside_nursery))


static void _do_minor_collection(bool commit)
{
    /* We must move out of the nursery any object found within the
       nursery.  All objects touched are either from the current
       transaction, or are from 'modified_old_objects'.  In all cases,
       we should only read and change objects belonging to the current
       segment.
    */

    dprintf(("minor_collection commit=%d\n", (int)commit));

    STM_PSEGMENT->minor_collect_will_commit_now = commit;
    if (!commit) {
        /* 'STM_PSEGMENT->overflow_number' is used now by this collection,
           in the sense that it's copied to the overflow objects */
        STM_PSEGMENT->overflow_number_has_been_used = true;
    }

    /* We need this to track the large overflow objects for a future
       commit.  We don't need it if we're committing now. */
    if (!commit && STM_PSEGMENT->large_overflow_objects == NULL)
        STM_PSEGMENT->large_overflow_objects = list_create();

    /* All the objects we move out of the nursery become "overflow"
       objects.  We use the list 'objects_pointing_to_nursery'
       to hold the ones we didn't trace so far. */
    if (STM_PSEGMENT->objects_pointing_to_nursery == NULL) {
        STM_PSEGMENT->objects_pointing_to_nursery = list_create();

        /* See the doc of 'objects_pointing_to_nursery': if it is NULL,
           then it is implicitly understood to be equal to
           'modified_old_objects'.  We could copy modified_old_objects
           into objects_pointing_to_nursery, but instead we use the
           following shortcut */
        collect_modified_old_objects();
    }

    collect_roots_in_nursery();

    collect_oldrefs_to_nursery();

    /* now all surviving nursery objects have been moved out */
    stm_move_young_weakrefs();

    throw_away_nursery(get_priv_segment(STM_SEGMENT->segment_num));

    assert(MINOR_NOTHING_TO_DO(STM_PSEGMENT));
    assert(list_is_empty(STM_PSEGMENT->objects_pointing_to_nursery));
}

static void minor_collection(bool commit)
{
    assert(!_has_mutex());

    stm_safe_point();

    change_timing_state(STM_TIME_MINOR_GC);

    _do_minor_collection(commit);

    change_timing_state(commit ? STM_TIME_BOOKKEEPING : STM_TIME_RUN_CURRENT);
}

void stm_collect(long level)
{
    if (level > 0)
        force_major_collection_request();

    minor_collection(/*commit=*/ false);
    major_collection_if_requested();
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
        stm_collect(0);
    }

    char *result = allocate_outside_nursery_large(size_rounded_up);
    object_t *o = (object_t *)(result - stm_object_pages);
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
    for (i = 1; i <= NB_SEGMENTS; i++) {
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

static void major_do_minor_collections(void)
{
    int original_num = STM_SEGMENT->segment_num;
    long i;

    for (i = 1; i <= NB_SEGMENTS; i++) {
        struct stm_priv_segment_info_s *pseg = get_priv_segment(i);
        if (MINOR_NOTHING_TO_DO(pseg))  /*TS_NONE segments have NOTHING_TO_DO*/
            continue;

        assert(pseg->transaction_state != TS_NONE);
        assert(pseg->safe_point != SP_RUNNING);
        assert(pseg->safe_point != SP_NO_TRANSACTION);

        set_gs_register(get_segment_base(i));

        /* Other segments that will abort immediately after resuming: we
           have to ignore them, not try to collect them anyway!
           Collecting might fail due to invalid state.
        */
        if (!must_abort()) {
            _do_minor_collection(/*commit=*/ false);
            assert(MINOR_NOTHING_TO_DO(pseg));
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

    /* always gets outside as a large object for now */
    char *allocated = allocate_outside_nursery_large(size);
    object_t *nobj = (object_t *)(allocated - stm_object_pages);

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
    return nobj;
}

static object_t *find_existing_shadow(object_t *obj)
{
    wlog_t *item;

    TREE_FIND(*STM_PSEGMENT->nursery_objects_shadows,
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
