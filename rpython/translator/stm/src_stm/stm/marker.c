/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


void (*stmcb_expand_marker)(char *segment_base, uintptr_t odd_number,
                            object_t *following_object,
                            char *outputbuf, size_t outputbufsize);

void (*stmcb_debug_print)(const char *cause, double time,
                          const char *marker);


static void marker_fetch(stm_thread_local_t *tl, uintptr_t marker[2])
{
    /* fetch the current marker from the tl's shadow stack,
       and return it in 'marker[2]'. */
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
        marker[0] = (uintptr_t)current[0].ss;
        marker[1] = (uintptr_t)current[1].ss;
    }
    else {
        /* no marker found */
        marker[0] = 0;
        marker[1] = 0;
    }
}

static void marker_expand(uintptr_t marker[2], char *segment_base,
                          char *outmarker)
{
    /* Expand the marker given by 'marker[2]' into a full string.  This
       works assuming that the marker was produced inside the segment
       given by 'segment_base'.  If that's from a different thread, you
       must first acquire the corresponding 'marker_lock'. */
    assert(_has_mutex());
    outmarker[0] = 0;
    if (marker[0] == 0)
        return;   /* no marker entry found */
    if (stmcb_expand_marker != NULL) {
        stmcb_expand_marker(segment_base, marker[0], (object_t *)marker[1],
                            outmarker, _STM_MARKER_LEN);
    }
}

static void marker_default_for_abort(struct stm_priv_segment_info_s *pseg)
{
    if (pseg->marker_self[0] != 0)
        return;   /* already collected an entry */

    uintptr_t marker[2];
    marker_fetch(pseg->pub.running_thread, marker);
    marker_expand(marker, pseg->pub.segment_base, pseg->marker_self);
    pseg->marker_other[0] = 0;
}

char *_stm_expand_marker(void)
{
    /* for tests only! */
    static char _result[_STM_MARKER_LEN];
    uintptr_t marker[2];
    _result[0] = 0;
    s_mutex_lock();
    marker_fetch(STM_SEGMENT->running_thread, marker);
    marker_expand(marker, STM_SEGMENT->segment_base, _result);
    s_mutex_unlock();
    return _result;
}

static void marker_copy(stm_thread_local_t *tl,
                        struct stm_priv_segment_info_s *pseg,
                        enum stm_time_e attribute_to, double time)
{
    /* Copies the marker information from pseg to tl.  This is called
       indirectly from abort_with_mutex(), but only if the lost time is
       greater than that of the previous recorded marker.  By contrast,
       pseg->marker_self has been filled already in all cases.  The
       reason for the two steps is that we must fill pseg->marker_self
       earlier than now (some objects may be GCed), but we only know
       here the total time it gets attributed.
    */
    if (stmcb_debug_print) {
        stmcb_debug_print(timer_names[attribute_to], time, pseg->marker_self);
    }
    if (time * 0.99 > tl->longest_marker_time) {
        tl->longest_marker_state = attribute_to;
        tl->longest_marker_time = time;
        memcpy(tl->longest_marker_self, pseg->marker_self, _STM_MARKER_LEN);
        memcpy(tl->longest_marker_other, pseg->marker_other, _STM_MARKER_LEN);
    }
    pseg->marker_self[0] = 0;
    pseg->marker_other[0] = 0;
}

static void marker_fetch_obj_write(uint8_t in_segment_num, object_t *obj,
                                   uintptr_t marker[2])
{
    assert(_has_mutex());

    /* here, we acquired the other thread's marker_lock, which means that:

       (1) it has finished filling 'modified_old_objects' after it sets
           up the write_locks[] value that we're conflicting with

       (2) it is not mutating 'modified_old_objects' right now (we have
           the global mutex_lock at this point too).
    */
    long i;
    struct stm_priv_segment_info_s *pseg = get_priv_segment(in_segment_num);
    struct list_s *mlst = pseg->modified_old_objects;
    struct list_s *mlstm = pseg->modified_old_objects_markers;
    for (i = list_count(mlst); --i >= 0; ) {
        if (list_item(mlst, i) == (uintptr_t)obj) {
            assert(list_count(mlstm) == 2 * list_count(mlst));
            marker[0] = list_item(mlstm, i * 2 + 0);
            marker[1] = list_item(mlstm, i * 2 + 1);
            return;
        }
    }
    marker[0] = 0;
    marker[1] = 0;
}

static void marker_contention(int kind, bool abort_other,
                              uint8_t other_segment_num, object_t *obj)
{
    uintptr_t self_marker[2];
    uintptr_t other_marker[2];
    struct stm_priv_segment_info_s *my_pseg, *other_pseg;

    my_pseg = get_priv_segment(STM_SEGMENT->segment_num);
    other_pseg = get_priv_segment(other_segment_num);

    char *my_segment_base = STM_SEGMENT->segment_base;
    char *other_segment_base = get_segment_base(other_segment_num);

    acquire_marker_lock(other_segment_base);

    /* Collect the location for myself.  It's usually the current
       location, except in a write-read abort, in which case it's the
       older location of the write. */
    if (kind == WRITE_READ_CONTENTION)
        marker_fetch_obj_write(my_pseg->pub.segment_num, obj, self_marker);
    else
        marker_fetch(my_pseg->pub.running_thread, self_marker);

    /* Expand this location into either my_pseg->marker_self or
       other_pseg->marker_other, depending on who aborts. */
    marker_expand(self_marker, my_segment_base,
                  abort_other ? other_pseg->marker_other
                              : my_pseg->marker_self);

    /* For some categories, we can also collect the relevant information
       for the other segment. */
    char *outmarker = abort_other ? other_pseg->marker_self
                                  : my_pseg->marker_other;
    switch (kind) {
    case WRITE_WRITE_CONTENTION:
        marker_fetch_obj_write(other_segment_num, obj, other_marker);
        marker_expand(other_marker, other_segment_base, outmarker);
        break;
    case INEVITABLE_CONTENTION:
        assert(abort_other == false);
        other_marker[0] = other_pseg->marker_inev[0];
        other_marker[1] = other_pseg->marker_inev[1];
        marker_expand(other_marker, other_segment_base, outmarker);
        break;
    case WRITE_READ_CONTENTION:
        strcpy(outmarker, "<read at unknown location>");
        break;
    default:
        outmarker[0] = 0;
        break;
    }

    release_marker_lock(other_segment_base);
}

static void marker_fetch_inev(void)
{
    uintptr_t marker[2];
    marker_fetch(STM_SEGMENT->running_thread, marker);
    STM_PSEGMENT->marker_inev[0] = marker[0];
    STM_PSEGMENT->marker_inev[1] = marker[1];
}
