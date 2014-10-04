/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


static void marker_fetch(stm_loc_marker_t *out_marker)
{
    /* Fetch the current marker from the 'out_marker->tl's shadow stack,
       and return it in 'out_marker->odd_number' and 'out_marker->object'. */
    stm_thread_local_t *tl = out_marker->tl;
    struct stm_shadowentry_s *current = tl->shadowstack - 1;
    struct stm_shadowentry_s *base = tl->shadowstack_base;

    /* The shadowstack_base contains -1, which is a convenient stopper for
       the loop below but which shouldn't be returned. */
    assert(base->ss == (object_t *)-1);

    while (!(((uintptr_t)current->ss) & 1)) {
        current--;
        assert(current >= base);
    }
    if (current != base) {
        /* found the odd marker */
        out_marker->odd_number = (uintptr_t)current[0].ss;
        out_marker->object = current[1].ss;
    }
    else {
        /* no marker found */
        out_marker->odd_number = 0;
        out_marker->object = NULL;
    }
}

static void _timing_fetch_inev(void)
{
    stm_loc_marker_t marker;
    marker.tl = STM_SEGMENT->running_thread;
    marker_fetch(&marker);
    STM_PSEGMENT->marker_inev.odd_number = marker.odd_number;
    STM_PSEGMENT->marker_inev.object = marker.object;
}

static void marker_fetch_obj_write(object_t *obj, stm_loc_marker_t *out_marker)
{
    /* From 'out_marker->tl', fill in 'out_marker->segment_base' and
       'out_marker->odd_number' and 'out_marker->object' from the
       marker associated with writing the 'obj'.
    */
    assert(_has_mutex());

    /* here, we acquired the other thread's marker_lock, which means that:

       (1) it has finished filling 'modified_old_objects' after it sets
           up the write_locks[] value that we're conflicting with

       (2) it is not mutating 'modified_old_objects' right now (we have
           the global mutex_lock at this point too).
    */
    long i;
    int in_segment_num = out_marker->tl->associated_segment_num;
    struct stm_priv_segment_info_s *pseg = get_priv_segment(in_segment_num);
    struct list_s *mlst = pseg->modified_old_objects;
    struct list_s *mlstm = pseg->modified_old_objects_markers;
    assert(list_count(mlstm) <= 2 * list_count(mlst));
    for (i = list_count(mlstm) / 2; --i >= 0; ) {
        if (list_item(mlst, i) == (uintptr_t)obj) {
            out_marker->odd_number = list_item(mlstm, i * 2 + 0);
            out_marker->object = (object_t *)list_item(mlstm, i * 2 + 1);
            return;
        }
    }
    out_marker->odd_number = 0;
    out_marker->object = NULL;
}

static void _timing_record_write(void)
{
    stm_loc_marker_t marker;
    marker.tl = STM_SEGMENT->running_thread;
    marker_fetch(&marker);

    long base_count = list_count(STM_PSEGMENT->modified_old_objects);
    struct list_s *mlstm = STM_PSEGMENT->modified_old_objects_markers;
    while (list_count(mlstm) < 2 * base_count) {
        mlstm = list_append2(mlstm, 0, 0);
    }
    mlstm = list_append2(mlstm, marker.odd_number, (uintptr_t)marker.object);
    STM_PSEGMENT->modified_old_objects_markers = mlstm;
}

static void _timing_contention(enum stm_event_e kind,
                               uint8_t other_segment_num, object_t *obj)
{
    struct stm_priv_segment_info_s *other_pseg;
    other_pseg = get_priv_segment(other_segment_num);

    char *other_segment_base = other_pseg->pub.segment_base;
    acquire_marker_lock(other_segment_base);

    stm_loc_marker_t markers[2];

    /* Collect the location for myself.  It's usually the current
       location, except in a write-read abort, in which case it's the
       older location of the write. */
    markers[0].tl = STM_SEGMENT->running_thread;
    markers[0].segment_base = STM_SEGMENT->segment_base;

    if (kind == STM_CONTENTION_WRITE_READ)
        marker_fetch_obj_write(obj, &markers[0]);
    else
        marker_fetch(&markers[0]);

    /* For some categories, we can also collect the relevant information
       for the other segment. */
    markers[1].tl = other_pseg->pub.running_thread;
    markers[1].segment_base = other_pseg->pub.segment_base;

    switch (kind) {
    case STM_CONTENTION_WRITE_WRITE:
        marker_fetch_obj_write(obj, &markers[1]);
        break;
    case STM_CONTENTION_INEVITABLE:
        markers[1].odd_number = other_pseg->marker_inev.odd_number;
        markers[1].object = other_pseg->marker_inev.object;
        break;
    default:
        markers[1].odd_number = 0;
        markers[1].object = NULL;
        break;
    }

    stmcb_timing_event(markers[0].tl, kind, markers);

    /* only release the lock after stmcb_timing_event(), otherwise it could
       run into race conditions trying to interpret 'markers[1].object' */
    release_marker_lock(other_segment_base);
}


void (*stmcb_timing_event)(stm_thread_local_t *tl, /* the local thread */
                           enum stm_event_e event,
                           stm_loc_marker_t *markers);
