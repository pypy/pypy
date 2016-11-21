/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif

static bool marker_fetch(stm_thread_local_t *tl, stm_loc_marker_t *out_marker)
{
    /* Fetch the current marker from tl's shadow stack,
       and return it in 'out_marker->odd_number' and 'out_marker->object'. */
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
        return true;
    }
    else {
        /* no marker found */
        out_marker->odd_number = 0;
        out_marker->object = NULL;
        return false;
    }
}

static void marker_fetch_obj_write(struct stm_undo_s *start,
                                   struct stm_undo_s *contention,
                                   stm_loc_marker_t *out_marker)
{
    /* Fill out 'out_marker->odd_number' and 'out_marker->object' from
       the marker just before 'contention' in the list starting at
       'start'.
    */
    while (contention != start) {
        --contention;
        if (contention->type == TYPE_POSITION_MARKER &&
            contention->type2 != TYPE_MODIFIED_HASHTABLE) {
            out_marker->odd_number = contention->marker_odd_number;
            out_marker->object = contention->marker_object;
            return;
        }
    }
    /* no position marker found... */
    out_marker->odd_number = 0;
    out_marker->object = NULL;
}

static void _timing_record_write_position(void)
{
    stm_loc_marker_t marker;
    if (!marker_fetch(STM_SEGMENT->running_thread, &marker))
        return;

    struct list_s *list = STM_PSEGMENT->modified_old_objects;
    uintptr_t i = STM_PSEGMENT->position_markers_last;
    if (i < list_count(list)) {
        struct stm_undo_s *undo = (struct stm_undo_s *)(list->items + i);
        if (undo->type == TYPE_POSITION_MARKER &&
            undo->marker_odd_number == marker.odd_number &&
            undo->marker_object == marker.object)
            return;    /* already up-to-date */
    }

    /* -2 is not odd */
    assert(marker.odd_number != (uintptr_t)TYPE_MODIFIED_HASHTABLE);

    acquire_modification_lock_wr(STM_SEGMENT->segment_num);
    STM_PSEGMENT->position_markers_last = list_count(list);
    STM_PSEGMENT->modified_old_objects = list_append3(
        list,
        TYPE_POSITION_MARKER,         /* type */
        marker.odd_number,            /* marker_odd_number */
        (uintptr_t)marker.object);    /* marker_object */
    release_modification_lock_wr(STM_SEGMENT->segment_num);
}

static void timing_write_read_contention(struct stm_undo_s *start,
                                         struct stm_undo_s *contention)
{
    if (stmcb_timing_event == NULL)
        return;

    stm_loc_marker_t marker;
    marker_fetch_obj_write(start, contention, &marker);
    stmcb_timing_event(STM_SEGMENT->running_thread,
                       STM_CONTENTION_WRITE_READ, &marker);
}

static void _timing_become_inevitable(void)
{
    stm_loc_marker_t marker;
    marker_fetch(STM_SEGMENT->running_thread, &marker);
    stmcb_timing_event(STM_SEGMENT->running_thread,
                       STM_BECOME_INEVITABLE, &marker);
}


void (*stmcb_timing_event)(stm_thread_local_t *tl, /* the local thread */
                           enum stm_event_e event,
                           stm_loc_marker_t *marker);
