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
    _cards_cleared_in_object(get_priv_segment(STM_SEGMENT->segment_num), nobj);
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

static void _cards_cleared_in_object(struct stm_priv_segment_info_s *pseg, object_t *obj)
{
#ifndef NDEBUG
    struct object_s *realobj = (struct object_s *)REAL_ADDRESS(pseg->pub.segment_base, obj);
    size_t size = stmcb_size_rounded_up(realobj);

    if (size < _STM_MIN_CARD_OBJ_SIZE)
        return;                 /* too small for cards */

    uintptr_t first_card_index = get_write_lock_idx((uintptr_t)obj);
    uintptr_t card_index = 1;
    uintptr_t last_card_index = get_index_to_card_index(size - 1); /* max valid index */

    OPT_ASSERT(write_locks[first_card_index] <= NB_SEGMENTS_MAX
               || write_locks[first_card_index] == 255); /* see gcpage.c */
    while (card_index <= last_card_index) {
        uintptr_t card_lock_idx = first_card_index + card_index;
        if (write_locks[card_lock_idx] != CARD_CLEAR) {
            /* could occur if the object is immediately re-locked by
               another thread */
            assert(write_locks[first_card_index] != 0);
        }
        card_index++;
    }

    assert(!(realobj->stm_flags & GCFLAG_CARDS_SET));
#endif
}

static void _verify_cards_cleared_in_all_lists(struct stm_priv_segment_info_s *pseg)
{
#ifndef NDEBUG
    LIST_FOREACH_R(
        pseg->modified_old_objects, object_t * /*item*/,
        _cards_cleared_in_object(pseg, item));

    if (pseg->large_overflow_objects) {
        LIST_FOREACH_R(
            pseg->large_overflow_objects, object_t * /*item*/,
            _cards_cleared_in_object(pseg, item));
    }
    if (pseg->objects_pointing_to_nursery) {
        LIST_FOREACH_R(
            pseg->objects_pointing_to_nursery, object_t * /*item*/,
            _cards_cleared_in_object(pseg, item));
    }
    LIST_FOREACH_R(
        pseg->old_objects_with_cards, object_t * /*item*/,
        _cards_cleared_in_object(pseg, item));
#endif
}

static void _reset_object_cards(struct stm_priv_segment_info_s *pseg,
                                object_t *obj, uint8_t mark_value,
                                bool mark_all)
{
#pragma push_macro("STM_PSEGMENT")
#pragma push_macro("STM_SEGMENT")
#undef STM_PSEGMENT
#undef STM_SEGMENT
    struct object_s *realobj = (struct object_s *)REAL_ADDRESS(pseg->pub.segment_base, obj);
    size_t size = stmcb_size_rounded_up(realobj);

    OPT_ASSERT(size >= _STM_MIN_CARD_OBJ_SIZE);
    assert(IMPLY(mark_value == CARD_CLEAR, !mark_all)); /* not necessary */
    assert(IMPLY(mark_all, mark_value == CARD_MARKED_OLD)); /* set *all* to OLD */
    assert(IMPLY(IS_OVERFLOW_OBJ(pseg, realobj),
                 mark_value == CARD_CLEAR)); /* overflows are always CLEARed */

    uintptr_t first_card_index = get_write_lock_idx((uintptr_t)obj);
    uintptr_t card_index = 1;
    uintptr_t last_card_index = get_index_to_card_index(size - 1); /* max valid index */

    OPT_ASSERT(write_locks[first_card_index] <= NB_SEGMENTS
               || write_locks[first_card_index] == 255); /* see gcpage.c */

    dprintf(("mark cards of %p, size %lu with %d, all: %d\n",
             obj, size, mark_value, mark_all));
    dprintf(("obj has %lu cards\n", last_card_index));
    while (card_index <= last_card_index) {
        uintptr_t card_lock_idx = first_card_index + card_index;

        if (mark_all || write_locks[card_lock_idx] != CARD_CLEAR) {
            /* dprintf(("mark card %lu,wl:%lu of %p with %d\n", */
            /*          card_index, card_lock_idx, obj, mark_value)); */
            write_locks[card_lock_idx] = mark_value;
        }
        card_index++;
    }

    realobj->stm_flags &= ~GCFLAG_CARDS_SET;

#pragma pop_macro("STM_SEGMENT")
#pragma pop_macro("STM_PSEGMENT")
}


static void _trace_card_object(object_t *obj)
{
    assert(!_is_in_nursery(obj));
    assert(obj->stm_flags & GCFLAG_CARDS_SET);
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);

    dprintf(("_trace_card_object(%p)\n", obj));
    bool obj_is_overflow = IS_OVERFLOW_OBJ(STM_PSEGMENT, obj);
    uint8_t mark_value = obj_is_overflow ? CARD_CLEAR : CARD_MARKED_OLD;

    struct object_s *realobj = (struct object_s *)REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    size_t size = stmcb_size_rounded_up(realobj);
    uintptr_t offset_itemsize[2];
    stmcb_get_card_base_itemsize(realobj, offset_itemsize);
    size = (size - offset_itemsize[0]) / offset_itemsize[1];

    uintptr_t first_card_index = get_write_lock_idx((uintptr_t)obj);
    uintptr_t card_index = 1;
    uintptr_t last_card_index = get_index_to_card_index(size - 1); /* max valid index */

    OPT_ASSERT(write_locks[first_card_index] <= NB_SEGMENTS_MAX
               || write_locks[first_card_index] == 255); /* see gcpage.c */

    /* XXX: merge ranges */
    while (card_index <= last_card_index) {
        uintptr_t card_lock_idx = first_card_index + card_index;
        if (write_locks[card_lock_idx] == CARD_MARKED) {
            /* clear or set to old: */
            write_locks[card_lock_idx] = mark_value;

            uintptr_t start = get_card_index_to_index(card_index);
            uintptr_t stop = get_card_index_to_index(card_index + 1);

            dprintf(("trace_cards on %p with start:%lu stop:%lu\n",
                     obj, start, stop));
            stmcb_trace_cards(realobj, &minor_trace_if_young,
                              start, stop);
        }

        /* all cards should be cleared on overflow objs */
        assert(IMPLY(obj_is_overflow,
                     write_locks[card_lock_idx] == CARD_CLEAR));

        card_index++;
    }
    obj->stm_flags &= ~GCFLAG_CARDS_SET;
}



static inline void _collect_now(object_t *obj)
{
    assert(!_is_young(obj));
    assert(!(obj->stm_flags & GCFLAG_CARDS_SET));

    dprintf(("_collect_now: %p\n", obj));

    if (!(obj->stm_flags & GCFLAG_WRITE_BARRIER)) {
        /* Trace the 'obj' to replace pointers to nursery with pointers
           outside the nursery, possibly forcing nursery objects out and
           adding them to 'objects_pointing_to_nursery' as well. */
        char *realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
        stmcb_trace((struct object_s *)realobj, &minor_trace_if_young);

        obj->stm_flags |= GCFLAG_WRITE_BARRIER;
    }
    /* else traced in collect_cardrefs_to_nursery if necessary */
}


static void collect_cardrefs_to_nursery(void)
{
    dprintf(("collect_cardrefs_to_nursery\n"));
    struct list_s *lst = STM_PSEGMENT->old_objects_with_cards;

    while (!list_is_empty(lst)) {
        object_t *obj = (object_t*)list_pop_item(lst);

        assert(!_is_young(obj));

        if (!(obj->stm_flags & GCFLAG_CARDS_SET)) {
            /* sometimes we remove the CARDS_SET in the WB slowpath, see core.c */
            continue;
        }

        /* traces cards, clears marked cards or marks them old if necessary */
        _trace_card_object(obj);

        assert(!(obj->stm_flags & GCFLAG_CARDS_SET));
    }
}

static void collect_oldrefs_to_nursery(void)
{
    dprintf(("collect_oldrefs_to_nursery\n"));
    struct list_s *lst = STM_PSEGMENT->objects_pointing_to_nursery;

    while (!list_is_empty(lst)) {
        uintptr_t obj_sync_now = list_pop_item(lst);
        object_t *obj = (object_t *)(obj_sync_now & ~FLAG_SYNC_LARGE);

        _collect_now(obj);
        assert(!(obj->stm_flags & GCFLAG_CARDS_SET));

        if (obj_sync_now & FLAG_SYNC_LARGE) {
            /* this was a large object.  We must either synchronize the
               object to other segments now (after we added the
               WRITE_BARRIER flag and traced into it to fix its
               content); or add the object to 'large_overflow_objects'.
            */
            struct stm_priv_segment_info_s *pseg = get_priv_segment(STM_SEGMENT->segment_num);
            if (STM_PSEGMENT->minor_collect_will_commit_now) {
                acquire_privatization_lock();
                synchronize_object_now(obj, true); /* ignore cards! */
                release_privatization_lock();
            } else {
                LIST_APPEND(STM_PSEGMENT->large_overflow_objects, obj);
            }
            _cards_cleared_in_object(pseg, obj);
        }

        /* the list could have moved while appending */
        lst = STM_PSEGMENT->objects_pointing_to_nursery;
    }
}

static void collect_modified_old_objects(void)
{
    dprintf(("collect_modified_old_objects\n"));
    LIST_FOREACH_R(
        STM_PSEGMENT->modified_old_objects, object_t * /*item*/,
        _collect_now(item));
}

static void collect_roots_from_markers(uintptr_t num_old)
{
    dprintf(("collect_roots_from_markers\n"));
    /* visit the marker objects */
    struct list_s *mlst = STM_PSEGMENT->modified_old_objects_markers;
    STM_PSEGMENT->modified_old_objects_markers_num_old = list_count(mlst);
    uintptr_t i, total = list_count(mlst);
    assert((total & 1) == 0);
    for (i = num_old + 1; i < total; i += 2) {
        minor_trace_if_young((object_t **)list_ptr_to_item(mlst, i));
    }
    if (STM_PSEGMENT->marker_inev[1]) {
        uintptr_t *pmarker_inev_obj = (uintptr_t *)
            REAL_ADDRESS(STM_SEGMENT->segment_base,
                         &STM_PSEGMENT->marker_inev[1]);
        minor_trace_if_young((object_t **)pmarker_inev_obj);
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

        TREE_LOOP_FORWARD(*pseg->young_outside_nursery, item) {
            object_t *obj = (object_t*)item->addr;
            assert(!_is_in_nursery(obj));

            /* mark slot as unread (it can only have the read marker
               in this segment) */
            ((struct stm_read_marker_s *)
             (pseg->pub.segment_base + (((uintptr_t)obj) >> 4)))->rm = 0;

            _stm_large_free(stm_object_pages + item->addr);
        } TREE_LOOP_END;

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
    /* We must move out of the nursery any object found within the
       nursery.  All objects touched are either from the current
       transaction, or are from 'modified_old_objects'.  In all cases,
       we should only read and change objects belonging to the current
       segment.
    */

    dprintf(("minor_collection commit=%d\n", (int)commit));

    acquire_marker_lock(STM_SEGMENT->segment_base);

    STM_PSEGMENT->minor_collect_will_commit_now = commit;
    if (!commit) {
        /* We should commit soon, probably. This is kind of a
           workaround for the broken stm_should_break_transaction of
           pypy that doesn't want to commit any more after a minor
           collection. It may, however, always be a good idea... */
        stmcb_commit_soon();

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
    uintptr_t num_old;
    if (STM_PSEGMENT->objects_pointing_to_nursery == NULL) {
        STM_PSEGMENT->objects_pointing_to_nursery = list_create();

        /* collect objs with cards, adds to objects_pointing_to_nursery
           and makes sure there are no objs with cards left in
           modified_old_objs */
        collect_cardrefs_to_nursery();

        /* See the doc of 'objects_pointing_to_nursery': if it is NULL,
           then it is implicitly understood to be equal to
           'modified_old_objects'.  We could copy modified_old_objects
           into objects_pointing_to_nursery, but instead we use the
           following shortcut */
        collect_modified_old_objects();
        num_old = 0;
    }
    else {
        collect_cardrefs_to_nursery();
        num_old = STM_PSEGMENT->modified_old_objects_markers_num_old;
    }

    collect_roots_from_markers(num_old);

    collect_roots_in_nursery();

    collect_oldrefs_to_nursery();
    assert(list_is_empty(STM_PSEGMENT->old_objects_with_cards));

    /* now all surviving nursery objects have been moved out */
    stm_move_young_weakrefs();

    throw_away_nursery(get_priv_segment(STM_SEGMENT->segment_num));

    assert(MINOR_NOTHING_TO_DO(STM_PSEGMENT));
    assert(list_is_empty(STM_PSEGMENT->objects_pointing_to_nursery));

    release_marker_lock(STM_SEGMENT->segment_base);
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
