/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif
#include "finalizer.h"

/************************************************************/

#define NURSERY_START         (FIRST_NURSERY_PAGE * 4096UL)
#define NURSERY_SIZE          (NB_NURSERY_PAGES * 4096UL)
#define NURSERY_END           (NURSERY_START + NURSERY_SIZE)

static uintptr_t _stm_nursery_start;


#define DEFAULT_FILL_MARK_NURSERY_BYTES   (NURSERY_SIZE / 4)

uintptr_t stm_fill_mark_nursery_bytes = DEFAULT_FILL_MARK_NURSERY_BYTES;

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

static inline bool _is_from_same_transaction(object_t *obj) {
    return _is_young(obj) || IS_OVERFLOW_OBJ(STM_PSEGMENT, obj);
}

long stm_can_move(object_t *obj)
{
    /* 'long' return value to avoid using 'bool' in the public interface */
    return _is_in_nursery(obj);
}


/************************************************************/
static object_t *find_existing_shadow(object_t *obj);
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
        //dprintf(("move %p -> %p\n", obj, nobj));

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

    /* if this is not during commit, we make them overflow objects
       and push them to other segments on commit. */
    assert(!(nobj->stm_flags & GCFLAG_WB_EXECUTED));
    assert((nobj->stm_flags & -GCFLAG_OVERFLOW_NUMBER_bit0) == 0);
    if (!STM_PSEGMENT->minor_collect_will_commit_now) {
        nobj->stm_flags |= STM_PSEGMENT->overflow_number;
    }

    /* Must trace the object later */
    LIST_APPEND(STM_PSEGMENT->objects_pointing_to_nursery, nobj_sync_now);
    _cards_cleared_in_object(get_priv_segment(STM_SEGMENT->segment_num), nobj, true);

    assert(IMPLY(obj_should_use_cards(STM_SEGMENT->segment_base, nobj),
                 (((uintptr_t)nobj) & 15) == 0));
}

static void _cards_cleared_in_object(struct stm_priv_segment_info_s *pseg, object_t *obj,
                                     bool strict) /* strict = MARKED_OLD not allowed */
{
#ifndef NDEBUG
    struct object_s *realobj = (struct object_s *)REAL_ADDRESS(pseg->pub.segment_base, obj);
    size_t size = stmcb_size_rounded_up(realobj);

    if (size < _STM_MIN_CARD_OBJ_SIZE)
        return;                 /* too small for cards */

    assert(!(realobj->stm_flags & GCFLAG_CARDS_SET));

    if (!stmcb_obj_supports_cards(realobj))
        return;

    uintptr_t offset_itemsize[2] = {0, 0};
    stmcb_get_card_base_itemsize(realobj, offset_itemsize);
    struct stm_read_marker_s *cards = get_read_marker(pseg->pub.segment_base, (uintptr_t)obj);
    uintptr_t card_index = 1;
    size_t real_idx_count = (size - offset_itemsize[0]) / offset_itemsize[1];
    uintptr_t last_card_index = get_index_to_card_index(real_idx_count - 1); /* max valid index */

    while (card_index <= last_card_index) {
        assert(cards[card_index].rm == CARD_CLEAR
               || (cards[card_index].rm != CARD_MARKED
                   && cards[card_index].rm < pseg->pub.transaction_read_version)
               || (!strict && cards[card_index].rm != CARD_MARKED));
        card_index++;
    }
#endif
}

static void _verify_cards_cleared_in_all_lists(struct stm_priv_segment_info_s *pseg)
{
#ifndef NDEBUG
    struct list_s *list = pseg->modified_old_objects;
    struct stm_undo_s *undo = (struct stm_undo_s *)list->items;
    struct stm_undo_s *end = (struct stm_undo_s *)(list->items + list->count);

    for (; undo < end; undo++) {
        if (undo->type == TYPE_POSITION_MARKER)
            continue;
        _cards_cleared_in_object(pseg, undo->object, false);
    }
    LIST_FOREACH_R(
        pseg->large_overflow_objects, object_t * /*item*/,
        _cards_cleared_in_object(pseg, item, false));
    LIST_FOREACH_R(
        pseg->objects_pointing_to_nursery, object_t * /*item*/,
        _cards_cleared_in_object(pseg, item, false));
    LIST_FOREACH_R(
        pseg->old_objects_with_cards_set, object_t * /*item*/,
        _cards_cleared_in_object(pseg, item, false));
#endif
}

static void _reset_object_cards(struct stm_priv_segment_info_s *pseg,
                                object_t *obj, uint8_t mark_value,
                                bool mark_all, bool really_clear)
{
#pragma push_macro("STM_PSEGMENT")
#pragma push_macro("STM_SEGMENT")
#undef STM_PSEGMENT
#undef STM_SEGMENT
    dprintf(("_reset_object_cards(%p, mark=%d, mark_all=%d, really_clear=%d)\n",
             obj, mark_value, mark_all, really_clear));
    struct object_s *realobj = (struct object_s *)REAL_ADDRESS(pseg->pub.segment_base, obj);
    size_t size = stmcb_size_rounded_up(realobj);
    OPT_ASSERT(size >= _STM_MIN_CARD_OBJ_SIZE);

    uintptr_t offset_itemsize[2];
    stmcb_get_card_base_itemsize(realobj, offset_itemsize);
    size = (size - offset_itemsize[0]) / offset_itemsize[1];

    /* really_clear only used for freed new objs in minor collections, as
       they need to clear cards even if they are set to transaction_read_version */
    assert(IMPLY(really_clear, mark_value == CARD_CLEAR && !mark_all));
    assert(IMPLY(mark_value == CARD_CLEAR, !mark_all)); /* not necessary */
    assert(IMPLY(mark_all,
                 mark_value == pseg->pub.transaction_read_version)); /* set *all* to OLD */

    struct stm_read_marker_s *cards = get_read_marker(pseg->pub.segment_base, (uintptr_t)obj);
    uintptr_t card_index = 1;
    uintptr_t last_card_index = get_index_to_card_index(size - 1); /* max valid index */

    /* dprintf(("mark cards of %p, size %lu with %d, all: %d\n",
                obj, size, mark_value, mark_all));
       dprintf(("obj has %lu cards\n", last_card_index));*/
    while (card_index <= last_card_index) {
        if (mark_all || cards[card_index].rm == CARD_MARKED
            || (really_clear && cards[card_index].rm != CARD_CLEAR)) {
            /* dprintf(("mark card %lu,wl:%lu of %p with %d\n", */
            /*          card_index, card_lock_idx, obj, mark_value)); */
            cards[card_index].rm = mark_value;
        }
        card_index++;
    }

    realobj->stm_flags &= ~GCFLAG_CARDS_SET;

#pragma pop_macro("STM_SEGMENT")
#pragma pop_macro("STM_PSEGMENT")
}


#define TRACE_FOR_MINOR_COLLECTION  (&minor_trace_if_young)


static void _trace_card_object(object_t *obj)
{
    assert(!_is_in_nursery(obj));
    assert(obj->stm_flags & GCFLAG_CARDS_SET);
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);

    dprintf(("_trace_card_object(%p)\n", obj));

    struct object_s *realobj = (struct object_s *)REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    size_t size = stmcb_size_rounded_up(realobj);
    uintptr_t offset_itemsize[2];
    stmcb_get_card_base_itemsize(realobj, offset_itemsize);
    size = (size - offset_itemsize[0]) / offset_itemsize[1];

    struct stm_read_marker_s *cards = get_read_marker(STM_SEGMENT->segment_base, (uintptr_t)obj);
    uintptr_t card_index = 1;
    uintptr_t last_card_index = get_index_to_card_index(size - 1); /* max valid index */

    /* XXX: merge ranges */
    while (card_index <= last_card_index) {
        if (cards[card_index].rm == CARD_MARKED) {
            /* clear or set to old: */
            cards[card_index].rm = STM_SEGMENT->transaction_read_version;

            uintptr_t start = get_card_index_to_index(card_index);
            uintptr_t stop = get_card_index_to_index(card_index + 1);
            if (card_index == last_card_index) {
                assert(stop >= size);
                stop = size;
            }
            else {
                assert(stop < size);
            }

            dprintf(("trace_cards on %p with start:%lu stop:%lu\n",
                     obj, start, stop));
            stmcb_trace_cards(realobj, TRACE_FOR_MINOR_COLLECTION,
                              start, stop);
        }

        card_index++;
    }
    obj->stm_flags &= ~GCFLAG_CARDS_SET;
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

    dprintf(("collect_roots_in_nursery:\n"));
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
        dprintf(("    %p: %p -> %p\n", current, (void *)x, current->ss));
    }

    minor_trace_if_young(&tl->thread_local_obj);
}


static inline void _collect_now(object_t *obj)
{
    assert(!_is_young(obj));
    assert(!(obj->stm_flags & GCFLAG_CARDS_SET));

    //dprintf(("_collect_now: %p\n", obj));

    if (!(obj->stm_flags & GCFLAG_WRITE_BARRIER)) {
        /* Trace the 'obj' to replace pointers to nursery with pointers
           outside the nursery, possibly forcing nursery objects out and
           adding them to 'objects_pointing_to_nursery' as well. */
        char *realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
        stmcb_trace((struct object_s *)realobj, TRACE_FOR_MINOR_COLLECTION);

        obj->stm_flags |= GCFLAG_WRITE_BARRIER;
    }
    /* else traced in collect_cardrefs_to_nursery if necessary */
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
        assert(!(obj->stm_flags & GCFLAG_CARDS_SET));

        if (obj_sync_now & FLAG_SYNC_LARGE) {
            /* XXX: SYNC_LARGE even set for small objs right now */
            /* this is a newly allocated obj in this transaction. We must
               either synchronize the object to other segments now, or
               add the object to large_overflow_objects list */
            struct stm_priv_segment_info_s *pseg = get_priv_segment(STM_SEGMENT->segment_num);
            if (pseg->minor_collect_will_commit_now) {
                acquire_privatization_lock(pseg->pub.segment_num);
                synchronize_object_enqueue(obj);
                release_privatization_lock(pseg->pub.segment_num);
            } else {
                LIST_APPEND(STM_PSEGMENT->large_overflow_objects, obj);
            }
            _cards_cleared_in_object(pseg, obj, false);
        }

        /* the list could have moved while appending */
        lst = STM_PSEGMENT->objects_pointing_to_nursery;
    }

    /* flush all overflow objects to other segments now */
    if (STM_PSEGMENT->minor_collect_will_commit_now) {
        acquire_privatization_lock(STM_SEGMENT->segment_num);
        synchronize_objects_flush();
        release_privatization_lock(STM_SEGMENT->segment_num);
    } else {
        /* nothing in the queue when not committing */
        assert(STM_PSEGMENT->sq_len == 0);
    }
}


static void collect_cardrefs_to_nursery(void)
{
    dprintf(("collect_cardrefs_to_nursery\n"));
    struct list_s *lst = STM_PSEGMENT->old_objects_with_cards_set;

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

static void collect_roots_from_markers(uintptr_t len_old)
{
    dprintf(("collect_roots_from_markers\n"));

    /* visit the marker objects */
    struct list_s *list = STM_PSEGMENT->modified_old_objects;
    struct stm_undo_s *undo = (struct stm_undo_s *)(list->items + len_old);
    struct stm_undo_s *end = (struct stm_undo_s *)(list->items + list->count);

    for (; undo < end; undo++) {
        /* this logic also works if type2 == TYPE_MODIFIED_HASHTABLE */
        if (undo->type == TYPE_POSITION_MARKER)
            minor_trace_if_young(&undo->marker_object);
    }
}

static void collect_young_objects_with_finalizers(void)
{
    /* for real finalizers: in a minor collection, all young objs must survive! */

    struct list_s *lst = STM_PSEGMENT->finalizers->probably_young_objects_with_finalizers;
    long i, count = list_count(lst);
    for (i = 0; i < count; i += 2) {
        object_t *obj = (object_t *)list_item(lst, i);
        uintptr_t qindex = list_item(lst, i + 1);

        minor_trace_if_young(&obj);

        LIST_APPEND(STM_PSEGMENT->finalizers->objects_with_finalizers, obj);
        LIST_APPEND(STM_PSEGMENT->finalizers->objects_with_finalizers, qindex);
    }
    list_clear(lst);
}



static void throw_away_nursery(struct stm_priv_segment_info_s *pseg)
{
#pragma push_macro("STM_PSEGMENT")
#pragma push_macro("STM_SEGMENT")
#undef STM_PSEGMENT
#undef STM_SEGMENT
    dprintf(("throw_away_nursery\n"));

    size_t nursery_used;
    nursery_used = pseg->pub.nursery_current - (stm_char *)_stm_nursery_start;
    if (nursery_used > NB_NURSERY_PAGES * 4096) {
        /* possible in rare cases when the program artificially advances
           its own nursery_current */
        nursery_used = NB_NURSERY_PAGES * 4096;
    }
    OPT_ASSERT((nursery_used & 7) == 0);

    /* reset the nursery by zeroing it */
    char *realnursery;
    realnursery = REAL_ADDRESS(pseg->pub.segment_base, _stm_nursery_start);
    (void)realnursery;
#if _STM_NURSERY_ZEROED
    memset(realnursery, 0, nursery_used);

    /* assert that the rest of the nursery still contains only zeroes */
    assert_memset_zero(realnursery + nursery_used,
                       (NURSERY_END - _stm_nursery_start) - nursery_used);

#else
# ifndef NDEBUG
    memset(realnursery, 0xa0, nursery_used);
# endif
#endif

    pseg->total_throw_away_nursery += nursery_used;
    pseg->pub.nursery_current = (stm_char *)_stm_nursery_start;
    pseg->pub.nursery_mark -= nursery_used;

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
                ((struct stm_read_marker_s *)
                 (pseg->pub.segment_base + (((uintptr_t)obj) >> 4)))->rm = 0;

                _stm_large_free(stm_object_pages + item->addr);
            } TREE_LOOP_END;
        }

        tree_clear(pseg->young_outside_nursery);
    }

    tree_clear(pseg->nursery_objects_shadows);
#pragma pop_macro("STM_SEGMENT")
#pragma pop_macro("STM_PSEGMENT")
}

#define MINOR_NOTHING_TO_DO(pseg)                                       \
    ((pseg)->pub.nursery_current == (stm_char *)_stm_nursery_start &&   \
     tree_is_cleared((pseg)->young_outside_nursery))


static void _do_minor_collection(bool commit)
{
    dprintf(("minor_collection commit=%d\n", (int)commit));
    assert(!STM_SEGMENT->no_safe_point_here);

    STM_PSEGMENT->minor_collect_will_commit_now = commit;

    uintptr_t len_old;
    if (STM_PSEGMENT->overflow_number_has_been_used)
        len_old = STM_PSEGMENT->position_markers_len_old;
    else
        len_old = 0;

    if (!commit) {
        /* 'STM_PSEGMENT->overflow_number' is used now by this collection,
           in the sense that it's copied to the overflow objects */
        STM_PSEGMENT->overflow_number_has_been_used = true;
        STM_PSEGMENT->position_markers_len_old =
            list_count(STM_PSEGMENT->modified_old_objects);
    }

    collect_cardrefs_to_nursery();

    collect_roots_from_markers(len_old);

    collect_roots_in_nursery();

    collect_young_objects_with_finalizers();

    if (STM_PSEGMENT->active_queues != NULL)
        collect_active_queues();

    collect_oldrefs_to_nursery();
    assert(list_is_empty(STM_PSEGMENT->old_objects_with_cards_set));

    /* now all surviving nursery objects have been moved out */
    acquire_privatization_lock(STM_SEGMENT->segment_num);
    stm_move_young_weakrefs();
    release_privatization_lock(STM_SEGMENT->segment_num);
    deal_with_young_objects_with_destructors();

    assert(list_is_empty(STM_PSEGMENT->objects_pointing_to_nursery));

    throw_away_nursery(get_priv_segment(STM_SEGMENT->segment_num));

    assert(MINOR_NOTHING_TO_DO(STM_PSEGMENT));
}

static void minor_collection(bool commit, bool external)
{
    assert(!_has_mutex());

    if (!external)
        stm_safe_point();

    timing_event(STM_SEGMENT->running_thread, STM_GC_MINOR_START);

    _do_minor_collection(commit);

    timing_event(STM_SEGMENT->running_thread, STM_GC_MINOR_DONE);
}

void stm_collect(long level)
{
    if (level > 0)
        force_major_collection_request();

    minor_collection(/*commit=*/ false, /*external=*/ false);

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
#if !_STM_NURSERY_ZEROED
        ((object_t *)p)->stm_flags = 0;
#endif
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

#if _STM_NURSERY_ZEROED
    memset(REAL_ADDRESS(STM_SEGMENT->segment_base, o), 0, size_rounded_up);
#else

#ifndef NDEBUG
    memset(REAL_ADDRESS(STM_SEGMENT->segment_base, o), 0xb0, size_rounded_up);
#endif

    o->stm_flags = 0;
    /* make all pages of 'o' accessible as synchronize_obj_flush() in minor
       collections assumes all young objs are fully accessible. */
    touch_all_pages_of_obj(o, size_rounded_up);
#endif
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

__attribute__((unused))
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

#if _STM_NURSERY_ZEROED
    assert_memset_zero(REAL_ADDRESS(STM_SEGMENT->segment_base,
                                    STM_SEGMENT->nursery_current),
                       NURSERY_END - _stm_nursery_start);
#endif
}


static void major_do_validation_and_minor_collections(void)
{
    int original_num = STM_SEGMENT->segment_num;
    long i;

    assert(_has_mutex());

    /* including the sharing seg0 */
    for (i = 0; i < NB_SEGMENTS; i++) {
        ensure_gs_register(i);

        bool ok = _stm_validate();
        assert(get_priv_segment(i)->last_commit_log_entry->next == NULL
               || get_priv_segment(i)->last_commit_log_entry->next == INEV_RUNNING);
        if (!ok) {
            if (STM_PSEGMENT->transaction_state == TS_NONE) {
                /* we found a segment that has stale read-marker data and thus
                   is in conflict with committed objs. Since it is not running
                   currently, it's fine to ignore it. */
                continue;
            }
            assert(i != 0);     /* sharing seg0 should never need an abort */

            /* tell it to abort when continuing */
            STM_PSEGMENT->pub.nursery_end = NSE_SIGABORT;
            assert(must_abort());

            dprintf(("abort data structures\n"));
            abort_data_structures_from_segment_num(i);
            continue;
        }


        if (MINOR_NOTHING_TO_DO(STM_PSEGMENT))
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

    ensure_gs_register(original_num);
}


static object_t *allocate_shadow(object_t *obj)
{
    char *realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    size_t size = stmcb_size_rounded_up((struct object_s *)realobj);

    /* always gets outside */
    object_t *nobj;
    if (size > GC_LAST_SMALL_SIZE) {
        /* case 1: object is not small enough.
           Ask gcpage.c for an allocation via largemalloc. */
        nobj = (object_t *)allocate_outside_nursery_large(size);
    } else {
        /* case "small enough" */
        nobj = (object_t *)allocate_outside_nursery_small(size);
    }

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
