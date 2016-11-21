/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif
char *stm_object_pages;
long _stm_segment_nb_pages = NB_PAGES;
int _stm_nb_segments = NB_SEGMENTS;
int _stm_psegment_ofs = (int)(uintptr_t)STM_PSEGMENT;

/* *** MISC *** */
static void free_bk(struct stm_undo_s *undo)
{
    assert(undo->type != TYPE_POSITION_MARKER);
    free(undo->backup);
    assert(undo->backup = (char*)0xbb);
    increment_total_allocated(-SLICE_SIZE(undo->slice));
}

static struct stm_commit_log_entry_s *malloc_cle(long entries)
{
    size_t byte_len = sizeof(struct stm_commit_log_entry_s) +
        entries * sizeof(struct stm_undo_s);
    struct stm_commit_log_entry_s *result = malloc(byte_len);
    increment_total_allocated(byte_len);
    return result;
}

static void free_cle(struct stm_commit_log_entry_s *e)
{
    size_t byte_len = sizeof(struct stm_commit_log_entry_s) +
        e->written_count * sizeof(struct stm_undo_s);
    increment_total_allocated(-byte_len);
    free(e);
}
/* *** MISC *** */


/* General helper: copies objects into our own segment, from some
   source described by a range of 'struct stm_undo_s'.  Maybe later
   we could specialize this function to avoid the checks in the
   inner loop.
*/
static void import_objects(
        int from_segnum,            /* or -1: from undo->backup,
                                       or -2: from undo->backup if not modified */
        uintptr_t pagenum,          /* or -1: "all accessible" */
        struct stm_undo_s *undo,
        struct stm_undo_s *end)
{
    char *src_segment_base = (from_segnum >= 0 ? get_segment_base(from_segnum)
                                               : NULL);

    assert(IMPLY(from_segnum >= 0, modification_lock_check_rdlock(from_segnum)));
    assert(modification_lock_check_wrlock(STM_SEGMENT->segment_num));

    long my_segnum = STM_SEGMENT->segment_num;
    DEBUG_EXPECT_SEGFAULT(false);
    for (; undo < end; undo++) {
        if (undo->type == TYPE_POSITION_MARKER)
            continue;
        object_t *obj = undo->object;
        stm_char *oslice = ((stm_char *)obj) + SLICE_OFFSET(undo->slice);
        uintptr_t current_page_num = ((uintptr_t)oslice) / 4096;

        if (pagenum == -1) {
            if (get_page_status_in(my_segnum, current_page_num) == PAGE_NO_ACCESS)
                continue;
        } else if (pagenum != current_page_num) {
            continue;
        }

        if (from_segnum == -2
            && _stm_was_read(obj)
            && (get_page_status_in(my_segnum, (uintptr_t)obj / 4096) == PAGE_ACCESSIBLE)
            && (obj->stm_flags & GCFLAG_WB_EXECUTED)) {
            /* called from stm_validate():
                > if not was_read(), we certainly didn't modify
                > if obj->stm_flags is not accessible, WB_EXECUTED cannot be set
                > if not WB_EXECUTED, we may have read from the obj in a different page but
                  did not modify it (should not occur right now, but future proof!)
               only the WB_EXECUTED alone is not enough, since we may have imported from a
               segment's private page (which had the flag set) */
            assert(IMPLY(_stm_was_read(obj), (obj->stm_flags & GCFLAG_WB_EXECUTED))); /* for now */
            continue;           /* only copy unmodified */
        }

        /* XXX: if the next assert is always true, we should never get a segfault
           in this function at all. So the DEBUG_EXPECT_SEGFAULT is correct. */
        assert((get_page_status_in(my_segnum, current_page_num) != PAGE_NO_ACCESS));

        /* dprintf(("import slice seg=%d obj=%p off=%lu sz=%d pg=%lu\n", */
        /*          from_segnum, obj, SLICE_OFFSET(undo->slice), */
        /*          SLICE_SIZE(undo->slice), current_page_num)); */
        char *src, *dst;
        if (src_segment_base != NULL)
            src = REAL_ADDRESS(src_segment_base, oslice);
        else
            src = undo->backup;
        dst = REAL_ADDRESS(STM_SEGMENT->segment_base, oslice);
        memcpy(dst, src, SLICE_SIZE(undo->slice));

        if (src_segment_base == NULL && SLICE_OFFSET(undo->slice) == 0) {
            /* check that restored obj doesn't have WB_EXECUTED */
            assert((get_page_status_in(my_segnum, (uintptr_t)obj / 4096) == PAGE_NO_ACCESS)
                   || !(obj->stm_flags & GCFLAG_WB_EXECUTED));
        }
    }
    DEBUG_EXPECT_SEGFAULT(true);
}



/* ############# commit log ############# */


void _dbg_print_commit_log(void)
{
    struct stm_commit_log_entry_s *cl = &commit_log_root;

    fprintf(stderr, "commit log:\n");
    while (cl) {
        fprintf(stderr, "  entry at %p: seg %d, rev %lu\n", cl, cl->segment_num, cl->rev_num);
        struct stm_undo_s *undo = cl->written;
        struct stm_undo_s *end = undo + cl->written_count;
        for (; undo < end; undo++) {
            if (undo->type == TYPE_POSITION_MARKER) {
                if (undo->type2 == TYPE_MODIFIED_HASHTABLE) {
                    fprintf(stderr, "    hashtable %p\n",
                            undo->modif_hashtable);
                }
                else {
                    fprintf(stderr, "    marker %p %lu\n",
                            undo->marker_object, undo->marker_odd_number);
                }
                continue;
            }
            fprintf(stderr, "    obj %p, size %d, ofs %lu: ", undo->object,
                    SLICE_SIZE(undo->slice), SLICE_OFFSET(undo->slice));
            /* long i; */
            /* for (i=0; i<SLICE_SIZE(undo->slice); i += 8) */
            /*     fprintf(stderr, " 0x%016lx", *(long *)(undo->backup + i)); */
            fprintf(stderr, "\n");
        }

        cl = cl->next;
        if (cl == INEV_RUNNING) {
            fprintf(stderr, "  INEVITABLE\n");
            return;
        }
    }
}

static void reset_modified_from_backup_copies(int segment_num, object_t *only_obj);  /* forward */
static void undo_modifications_to_single_obj(int segment_num, object_t *only_obj); /* forward */

static bool _stm_validate(void)
{
    /* returns true if we reached a valid state, or false if
       we need to abort now */
    dprintf(("_stm_validate() at cl=%p, rev=%lu\n", STM_PSEGMENT->last_commit_log_entry,
             STM_PSEGMENT->last_commit_log_entry->rev_num));
    /* go from last known entry in commit log to the
       most current one and apply all changes done
       by other transactions. Abort if we have read one of
       the committed objs. */
    struct stm_commit_log_entry_s *first_cl = STM_PSEGMENT->last_commit_log_entry;
    struct stm_commit_log_entry_s *next_cl, *last_cl, *cl;
    int my_segnum = STM_SEGMENT->segment_num;
    /* Don't check this 'cl'. This entry is already checked */

    if (STM_PSEGMENT->transaction_state == TS_INEVITABLE) {
        assert(first_cl->next == INEV_RUNNING);
        return true;
    }

    bool needs_abort = false;

    if (STM_PSEGMENT->transaction_state == TS_NONE) {
        /* can be seen from major_do_validation_and_minor_collections();
           don't try to detect pseudo-conflicts in this case */
        needs_abort = true;
    }

    while(1) {
        /* retry IF: */
        /* if at the time of "HERE" (s.b.) there happen to be
           more commits (and bk copies) then it could be that
           copy_bk_objs_in_page_from (s.b.) reads a bk copy that
           is itself more recent than last_cl. This is fixed
           by re-validating. */
        first_cl = STM_PSEGMENT->last_commit_log_entry;
        if (first_cl->next == NULL)
            break;

        if (first_cl->next == INEV_RUNNING) {
            /* need to reach safe point if an INEV transaction
               is waiting for us, otherwise deadlock */
            break;
        }

        /* Find the set of segments we need to copy from and lock them: */
        uint64_t segments_to_lock = 0;
        cl = first_cl;
        while ((next_cl = cl->next) != NULL) {
            if (next_cl == INEV_RUNNING) {
                /* only validate entries up to INEV */
                break;
            }
            assert(next_cl->rev_num > cl->rev_num);
            cl = next_cl;

            if (cl->written_count) {
                segments_to_lock |= (1UL << cl->segment_num);
            }
        }
        last_cl = cl;

        /* HERE */

        acquire_privatization_lock(my_segnum);
        acquire_modification_lock_set(segments_to_lock, my_segnum);


        /* import objects from first_cl to last_cl: */
        if (first_cl != last_cl) {
            uint64_t segment_really_copied_from = 0UL;

            cl = first_cl;
            while ((cl = cl->next) != NULL) {
                if (!needs_abort) {
                    struct stm_undo_s *undo = cl->written;
                    struct stm_undo_s *end = cl->written + cl->written_count;
                    for (; undo < end; undo++) {
                        object_t *obj;

                        if (LIKELY(undo->type != TYPE_POSITION_MARKER)) {
                            /* common case: 'undo->object' was written to
                               in this past commit, so we must check that
                               it was not read by us. */
                            obj = undo->object;
                        }
                        else if (undo->type2 != TYPE_MODIFIED_HASHTABLE)
                            continue;
                        else {
                            /* the previous stm_undo_s is about a written
                               'entry' object, which belongs to the hashtable
                               given now.  Check that we haven't read the
                               hashtable (via stm_hashtable_list()). */
                            obj = undo->modif_hashtable;
                        }

                        if (LIKELY(!_stm_was_read(obj)))
                            continue;

                        /* check for NO_CONFLICT flag in seg0. While its data may
                           not be current there, the flag will be there and is
                           immutable. (we cannot check in my_segnum bc. we may
                           only have executed stm_read(o) but not touched its pages
                           yet -> they may be NO_ACCESS */
                        struct object_s *obj0 = (struct object_s *)REAL_ADDRESS(get_segment_base(0), obj);
                        if (obj0->stm_flags & GCFLAG_NO_CONFLICT) {
                            /* obj is noconflict and therefore shouldn't cause
                               an abort. However, from now on, we also assume
                               that an abort would not roll-back to what is in
                               the backup copy, as we don't trace the bkcpy
                               during major GCs. (Seg0 may contain the version
                               found in the other segment and thus not have to
                               content of our bk_copy)

                               We choose the approach to reset all our changes
                               to this obj here, so that we can throw away the
                               backup copy completely: */
                            /* XXX: this browses through the whole list of modified
                               fragments; this may become a problem... */
                            undo_modifications_to_single_obj(my_segnum, obj);

                            continue;
                        }

                        /* conflict! */
                        dprintf(("_stm_validate() failed for obj %p\n", obj));

                        /* first reset all modified objects from the backup
                           copies as soon as the first conflict is detected;
                           then we will proceed below to update our segment
                           from the old (but unmodified) version to the newer
                           version.
                        */
                        reset_modified_from_backup_copies(my_segnum, NULL);
                        timing_write_read_contention(cl->written, undo);
                        needs_abort = true;
                        break;
                    }
                }

                if (cl->written_count) {
                    struct stm_undo_s *undo = cl->written;
                    struct stm_undo_s *end = cl->written + cl->written_count;

                    segment_really_copied_from |= (1UL << cl->segment_num);

                    import_objects(cl->segment_num, -1, undo, end);

                    /* here we can actually have our own modified version, so
                       make sure to only copy things that are not modified in our
                       segment... (if we do not abort) */
                    copy_bk_objs_in_page_from
                        (cl->segment_num, -1,     /* any page */
                         !needs_abort);  /* if we abort, we still want to copy everything */
                }

                dprintf(("_stm_validate() to cl=%p, rev=%lu\n", cl, cl->rev_num));
                /* last fully validated entry */
                STM_PSEGMENT->last_commit_log_entry = cl;
                if (cl == last_cl)
                    break;
            }
            assert(cl == last_cl);

            /* XXX: this optimization fails in test_basic.py, bug3 */
            /* OPT_ASSERT(segment_really_copied_from < (1 << NB_SEGMENTS)); */
            /* int segnum; */
            /* for (segnum = 1; segnum < NB_SEGMENTS; segnum++) { */
            /*     if (segment_really_copied_from & (1UL << segnum)) { */
            /*         /\* here we can actually have our own modified version, so */
            /*            make sure to only copy things that are not modified in our */
            /*            segment... (if we do not abort) *\/ */
            /*         copy_bk_objs_in_page_from( */
            /*             segnum, -1,     /\* any page *\/ */
            /*             !needs_abort);  /\* if we abort, we still want to copy everything *\/ */
            /*     } */
            /* } */
        }

        /* done with modifications */
        release_modification_lock_set(segments_to_lock, my_segnum);
        release_privatization_lock(my_segnum);
    }

    return !needs_abort;
}


static struct stm_commit_log_entry_s *_create_commit_log_entry(void)
{
    /* puts all modified_old_objects in a new commit log entry */

    // we don't need the privatization lock, as we are only
    // reading from modified_old_objs and nobody but us can change it
    struct list_s *list = STM_PSEGMENT->modified_old_objects;
    OPT_ASSERT((list_count(list) % 3) == 0);
    size_t count = list_count(list) / 3;
    struct stm_commit_log_entry_s *result = malloc_cle(count);

    result->next = NULL;
    result->segment_num = STM_SEGMENT->segment_num;
    result->rev_num = -1;       /* invalid */
    result->written_count = count;
    memcpy(result->written, list->items, count * sizeof(struct stm_undo_s));
    return result;
}


static void reset_wb_executed_flags(void);
static void readd_wb_executed_flags(void);
static void check_all_write_barrier_flags(char *segbase, struct list_s *list);

static void wait_for_inevitable(void)
{
    intptr_t detached = 0;

    s_mutex_lock();
 wait_some_more:
    if (safe_point_requested()) {
        /* XXXXXX if the safe point below aborts, in
           _validate_and_attach(), 'new' leaks */
        enter_safe_point_if_requested();
    }
    else if (STM_PSEGMENT->last_commit_log_entry->next == INEV_RUNNING) {
        /* loop until C_SEGMENT_FREE_OR_SAFE_POINT_REQ is signalled, but
           try to detach an inevitable transaction regularly */
        detached = fetch_detached_transaction();
        if (detached == 0) {
            EMIT_WAIT(STM_WAIT_OTHER_INEVITABLE);
            if (!cond_wait_timeout(C_SEGMENT_FREE_OR_SAFE_POINT_REQ, 0.00001))
                goto wait_some_more;
        }
    }
    EMIT_WAIT_DONE();
    s_mutex_unlock();

    if (detached != 0)
        commit_fetched_detached_transaction(detached);
}

/* This is called to do stm_validate() and then attach 'new' at the
   head of the 'commit_log_root' chained list.  This function sleeps
   and retries until it succeeds or aborts.
*/
static void _validate_and_attach(struct stm_commit_log_entry_s *new)
{
    uintptr_t cle_length = 0;
    struct stm_commit_log_entry_s *old;

    OPT_ASSERT(new != NULL);
    OPT_ASSERT(new != INEV_RUNNING);

    cle_length = list_count(STM_PSEGMENT->modified_old_objects);
    assert(cle_length == new->written_count * 3);

    soon_finished_or_inevitable_thread_segment();

 retry_from_start:
    if (!_stm_validate()) {
        free_cle(new);
        stm_abort_transaction();
    }

    if (cle_length != list_count(STM_PSEGMENT->modified_old_objects)) {
        /* something changed the list of modified objs during _stm_validate; or
         * during a major GC that also does _stm_validate(). That "something"
         * can only be a reset of a noconflict obj. Thus, we recreate the CL
         * entry */
        free_cle(new);
        new = _create_commit_log_entry();
        cle_length = list_count(STM_PSEGMENT->modified_old_objects);
    }

#if STM_TESTS
    if (STM_PSEGMENT->transaction_state != TS_INEVITABLE
        && STM_PSEGMENT->last_commit_log_entry->next == INEV_RUNNING) {
        /* abort for tests... */
        stm_abort_transaction();
    }
#endif

    if (STM_PSEGMENT->last_commit_log_entry->next == INEV_RUNNING) {
        wait_for_inevitable();
        goto retry_from_start;   /* redo _stm_validate() now */
    }

    /* we must not remove the WB_EXECUTED flags before validation as
       it is part of a condition in import_objects() called by
       copy_bk_objs_in_page_from to not overwrite our modifications.
       So we do it here: */
    reset_wb_executed_flags();
    check_all_write_barrier_flags(STM_SEGMENT->segment_base,
                                  STM_PSEGMENT->modified_old_objects);

    /* need to remove the entries in modified_old_objects "at the same
       time" as the attach to commit log. Otherwise, another thread may
       see the new CL entry, import it, look for backup copies in this
       segment and find the old backup copies! */
    acquire_modification_lock_wr(STM_SEGMENT->segment_num);

    /* try to attach to commit log: */
    old = STM_PSEGMENT->last_commit_log_entry;
    new->rev_num = old->rev_num + 1;
    if (__sync_bool_compare_and_swap(&old->next, NULL, new)) {
        /* success! */
        /* compare with _validate_and_add_to_commit_log */
        list_clear(STM_PSEGMENT->modified_old_objects);
        STM_PSEGMENT->last_commit_log_entry = new;
        release_modification_lock_wr(STM_SEGMENT->segment_num);
    }
    else {
        /* fail */
        release_modification_lock_wr(STM_SEGMENT->segment_num);
        /* XXX: unfortunately, if we failed to attach our CL entry,
           we have to re-add the WB_EXECUTED flags before we try to
           validate again because of said condition (s.a) */
        readd_wb_executed_flags();

        dprintf(("_validate_and_attach(%p) failed, retrying\n", new));
        goto retry_from_start;
    }
}

/* This is called to do stm_validate() and then attach INEV_RUNNING to
   the head of the 'commit_log_root' chained list.  This function
   may succeed or fail (or abort).
*/
static bool _validate_and_turn_inevitable(void)
{
    struct stm_commit_log_entry_s *old;

    if (!_stm_validate())
        stm_abort_transaction();

    /* try to attach to commit log: */
    old = STM_PSEGMENT->last_commit_log_entry;
    return __sync_bool_compare_and_swap(&old->next, NULL, INEV_RUNNING);
}

static void _validate_and_add_to_commit_log(void)
{
    struct stm_commit_log_entry_s *old, *new;

    new = _create_commit_log_entry();
    if (STM_PSEGMENT->transaction_state == TS_INEVITABLE) {
        assert(_stm_detached_inevitable_from_thread == 0  /* running it */
               || _stm_detached_inevitable_from_thread == -1);  /* committing external */

        old = STM_PSEGMENT->last_commit_log_entry;
        new->rev_num = old->rev_num + 1;
        OPT_ASSERT(old->next == INEV_RUNNING);

        /* WB_EXECUTED must be removed before we attach */
        reset_wb_executed_flags();
        check_all_write_barrier_flags(STM_SEGMENT->segment_base,
                                      STM_PSEGMENT->modified_old_objects);

        /* compare with _validate_and_attach: */
        acquire_modification_lock_wr(STM_SEGMENT->segment_num);
        list_clear(STM_PSEGMENT->modified_old_objects);
        STM_PSEGMENT->last_commit_log_entry = new;

        /* do it: */
        bool yes = __sync_bool_compare_and_swap(&old->next, INEV_RUNNING, new);
        OPT_ASSERT(yes);

        release_modification_lock_wr(STM_SEGMENT->segment_num);
    }
    else {
        _validate_and_attach(new);
    }
}

/* ############# STM ############# */
void stm_validate()
{
    if (!_stm_validate())
        stm_abort_transaction();
}


bool obj_should_use_cards(char *seg_base, object_t *obj)
{
    if (is_small_uniform(obj))
        return false;

    struct object_s *realobj = (struct object_s *)
        REAL_ADDRESS(seg_base, obj);
    long supports = stmcb_obj_supports_cards(realobj);
    if (!supports)
        return false;

    /* check also if it makes sense: */
    size_t size = stmcb_size_rounded_up(realobj);
    return (size >= _STM_MIN_CARD_OBJ_SIZE);
}


static void make_bk_slices_for_range(
    object_t *obj,
    stm_char *start, stm_char *end) /* [start, end[ */
{
    dprintf(("make_bk_slices_for_range(%p, %lu, %lu)\n",
             obj, start - (stm_char*)obj, end - start));
    timing_record_write_position();

    char *realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    uintptr_t first_page = ((uintptr_t)start) / 4096UL;
    uintptr_t end_page = ((uintptr_t)end) / 4096UL;

    uintptr_t page;
    uintptr_t slice_sz;
    uintptr_t slice_off = start - (stm_char*)obj;
    uintptr_t in_page_offset = (uintptr_t)start % 4096UL;
    uintptr_t remaining_obj_sz = end - start;
    for (page = first_page; page <= end_page && remaining_obj_sz; page++) {
        slice_sz = remaining_obj_sz;
        if (in_page_offset + slice_sz > 4096UL) {
            /* not over page boundaries */
            slice_sz = 4096UL - in_page_offset;
        }

        remaining_obj_sz -= slice_sz;
        in_page_offset = (in_page_offset + slice_sz) % 4096UL; /* mostly 0 */

        /* make backup slice: */
        char *bk_slice = malloc(slice_sz);
        increment_total_allocated(slice_sz);
        memcpy(bk_slice, realobj + slice_off, slice_sz);

        acquire_modification_lock_wr(STM_SEGMENT->segment_num);
        /* !! follows layout of "struct stm_undo_s" !! */
        STM_PSEGMENT->modified_old_objects = list_append3(
            STM_PSEGMENT->modified_old_objects,
            (uintptr_t)obj,     /* obj */
            (uintptr_t)bk_slice,  /* bk_addr */
            NEW_SLICE(slice_off, slice_sz));
        dprintf(("> append slice %p, off=%lu, sz=%lu\n", bk_slice, slice_off, slice_sz));
        release_modification_lock_wr(STM_SEGMENT->segment_num);

        slice_off += slice_sz;
    }

}

static void make_bk_slices(object_t *obj,
                           bool first_call, /* tells us if we also need to make a bk
                                               of the non-array part of the object */
                           uintptr_t index,  /* index == -1: all cards, index == -2: no cards */
                           bool do_missing_cards /* only bk the cards that don't have a bk */
                           )
{
    dprintf(("make_bk_slices(%p, %d, %ld, %d)\n", obj, first_call, index, do_missing_cards));
    /* do_missing_cards also implies that all cards are cleared at the end */
    /* index == -1 but not do_missing_cards: bk whole obj */
    assert(IMPLY(index == -2, first_call && !do_missing_cards));
    assert(IMPLY(index == -1 && !do_missing_cards, first_call));
    assert(IMPLY(do_missing_cards, index == -1));
    assert(IMPLY(is_small_uniform(obj), index == -1 && !do_missing_cards && first_call));
    assert(IMPLY(first_call, !do_missing_cards));
    assert(IMPLY(index != -1, obj_should_use_cards(STM_SEGMENT->segment_base, obj)));

    /* get whole card range */
    struct object_s *realobj = (struct object_s*)REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    size_t obj_size = stmcb_size_rounded_up(realobj);
    uintptr_t offset_itemsize[2] = {-1, -1};

    /* decide where to start copying: */
    size_t start_offset;
    if (first_call) {
        start_offset = 0;

        /* flags like a never-touched obj */
        assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);
        assert(!(obj->stm_flags & GCFLAG_WB_EXECUTED));
    } else {
        start_offset = -1;
    }

    /* decide if we don't want to look at cards at all: */
    if ((index == -1 || index == -2) && !do_missing_cards) {
        assert(first_call);
        if (index == -1) {
            /* whole obj */
            make_bk_slices_for_range(obj, (stm_char*)obj + start_offset,
                                     (stm_char*)obj + obj_size);
            if (obj_should_use_cards(STM_SEGMENT->segment_base, obj)) {
                /* mark whole obj as MARKED_OLD so we don't do bk slices anymore */
                _reset_object_cards(get_priv_segment(STM_SEGMENT->segment_num),
                                    obj, STM_SEGMENT->transaction_read_version,
                                    true, false);
            }
        } else {
            /* only fixed part */
            stmcb_get_card_base_itemsize(realobj, offset_itemsize);
            make_bk_slices_for_range(obj, (stm_char*)obj + start_offset,
                                     (stm_char*)obj + offset_itemsize[0]);
        }
        return;
    }

    stmcb_get_card_base_itemsize(realobj, offset_itemsize);

    size_t real_idx_count = (obj_size - offset_itemsize[0]) / offset_itemsize[1];
    assert(IMPLY(index != -1 && index != -2, index >= 0 && index < real_idx_count));
    struct stm_read_marker_s *cards = get_read_marker(STM_SEGMENT->segment_base, (uintptr_t)obj);
    uintptr_t last_card_index = get_index_to_card_index(real_idx_count - 1); /* max valid index */
    uintptr_t card_index;

    /* decide if we want only a specific card: */
    if (index != -1) {
        if (start_offset != -1) {
            /* bk fixed part separately: */
            make_bk_slices_for_range(obj, (stm_char*)obj + start_offset,
                                     (stm_char*)obj + offset_itemsize[0]);
        }

        card_index = get_index_to_card_index(index);

        size_t card_offset = offset_itemsize[0]
            + get_card_index_to_index(card_index) * offset_itemsize[1];
        size_t after_card_offset = offset_itemsize[0]
            + get_card_index_to_index(card_index + 1) * offset_itemsize[1];

        if (after_card_offset > obj_size)
            after_card_offset = obj_size;

        make_bk_slices_for_range(
            obj, (stm_char*)obj + card_offset, (stm_char*)obj + after_card_offset);

        return;
    }

    /* look for CARD_CLEAR or some non-transaction_read_version cards
       and make bk slices for them */
    assert(do_missing_cards && index == -1 && start_offset == -1);
    card_index = 1;
    uintptr_t start_card_index = -1;
    while (card_index <= last_card_index) {
        uint8_t card_value = cards[card_index].rm;

        if (card_value == CARD_CLEAR
            || (card_value != CARD_MARKED
                && card_value < STM_SEGMENT->transaction_read_version)) {
            /* we need a backup of this card */
            if (start_card_index == -1) {   /* first unmarked card */
                start_card_index = card_index;
            }
        } else {
            /* "CARD_MARKED_OLD" or CARD_MARKED */
            OPT_ASSERT(card_value == STM_SEGMENT->transaction_read_version
                       || card_value == CARD_MARKED);
        }
        /* in any case, remember that we already made a bk slice for this
           card, so set to "MARKED_OLD": */
        cards[card_index].rm = STM_SEGMENT->transaction_read_version;


        if (start_card_index != -1                    /* something to copy */
            && (card_value == CARD_MARKED             /* found marked card */
                || card_value == STM_SEGMENT->transaction_read_version/* old marked */
                || card_index == last_card_index)) {  /* this is the last card */

            /* do the bk slice: */
            uintptr_t copy_size;
            uintptr_t next_card_offset;
            uintptr_t start_card_offset;
            uintptr_t next_card_index = card_index;

            if (card_value == CARD_CLEAR
                || (card_value != CARD_MARKED
                    && card_value < STM_SEGMENT->transaction_read_version)) {
                /* this was actually the last card which wasn't set, but we
                   need to go one further to get the right offset */
                next_card_index++;
            }

            start_card_offset = offset_itemsize[0] +
                get_card_index_to_index(start_card_index) * offset_itemsize[1];

            next_card_offset = offset_itemsize[0] +
                get_card_index_to_index(next_card_index) * offset_itemsize[1];

            if (next_card_offset > obj_size)
                next_card_offset = obj_size;

            copy_size = next_card_offset - start_card_offset;
            OPT_ASSERT(copy_size > 0);

            /* add the slices: */
            make_bk_slices_for_range(
                obj, (stm_char*)obj + start_card_offset,
                (stm_char*)obj + next_card_offset);

            start_card_index = -1;
        }

        card_index++;
    }

    obj->stm_flags &= ~GCFLAG_CARDS_SET;
    _cards_cleared_in_object(get_priv_segment(STM_SEGMENT->segment_num), obj, false);
}

static void write_slowpath_overflow_obj(object_t *obj, bool mark_card)
{
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);
    assert(!(obj->stm_flags & GCFLAG_WB_EXECUTED));
    dprintf(("write_slowpath_overflow_obj(%p)\n", obj));

    if (!mark_card) {
        /* The basic case, with no card marking.  We append the object
           into 'objects_pointing_to_nursery', and remove the flag so
           that the write_slowpath will not be called again until the
           next minor collection. */
        if (obj->stm_flags & GCFLAG_CARDS_SET) {
            /* if we clear this flag, we also need to clear the cards.
               bk_slices are not needed as this is an overflow object */
            _reset_object_cards(get_priv_segment(STM_SEGMENT->segment_num),
                                obj, CARD_CLEAR, false, false);
        }
        obj->stm_flags &= ~(GCFLAG_WRITE_BARRIER | GCFLAG_CARDS_SET);
        LIST_APPEND(STM_PSEGMENT->objects_pointing_to_nursery, obj);
    } else {
        /* Card marking.  Don't remove GCFLAG_WRITE_BARRIER because we
           need to come back to _stm_write_slowpath_card() for every
           card to mark.  Add GCFLAG_CARDS_SET.
           again, we don't need bk_slices as this is an overflow obj */
        assert(!(obj->stm_flags & GCFLAG_CARDS_SET));
        obj->stm_flags |= GCFLAG_CARDS_SET;
        LIST_APPEND(STM_PSEGMENT->old_objects_with_cards_set, obj);
    }
}


static void touch_all_pages_of_obj(object_t *obj, size_t obj_size)
{
    /* XXX: make this function not needed */
    int my_segnum = STM_SEGMENT->segment_num;
    uintptr_t end_page, first_page = ((uintptr_t)obj) / 4096UL;

    /* get the last page containing data from the object */
    if (LIKELY(is_small_uniform(obj))) {
        end_page = first_page;
    } else {
        end_page = (((uintptr_t)obj) + obj_size - 1) / 4096UL;
    }

    acquire_privatization_lock(STM_SEGMENT->segment_num);
    uintptr_t page;
    for (page = first_page; page <= end_page; page++) {
        if (get_page_status_in(my_segnum, page) == PAGE_NO_ACCESS) {
            release_privatization_lock(STM_SEGMENT->segment_num);
            /* emulate pagefault -> PAGE_ACCESSIBLE: */
            handle_segfault_in_page(page);
            acquire_privatization_lock(STM_SEGMENT->segment_num);
        }
    }
    release_privatization_lock(STM_SEGMENT->segment_num);
}

static void write_slowpath_common(object_t *obj, bool mark_card)
{
    assert(_seems_to_be_running_transaction());
    assert(!_is_in_nursery(obj));
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);

    if (IS_OVERFLOW_OBJ(STM_PSEGMENT, obj)) {
        /* already executed WB once in this transaction. do GC
           part again: */
        assert(!(obj->stm_flags & GCFLAG_WB_EXECUTED));
        write_slowpath_overflow_obj(obj, mark_card);
        return;
    }

    dprintf(("write_slowpath(%p)\n", obj));

    /* add to read set: */
    stm_read(obj);

    if (!(obj->stm_flags & GCFLAG_WB_EXECUTED)) {
        /* the first time we write this obj, make sure it is fully
           accessible, as major gc may depend on being able to trace
           the full obj in this segment (XXX) */
        char *realobj;
        size_t obj_size;
        realobj = REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
        obj_size = stmcb_size_rounded_up((struct object_s *)realobj);

        touch_all_pages_of_obj(obj, obj_size);
    }

    if (mark_card) {
        if (!(obj->stm_flags & GCFLAG_WB_EXECUTED)) {
            make_bk_slices(obj,
                           true,        /* first_call */
                           -2,          /* index: backup only fixed part */
                           false);      /* do_missing_cards */
        }

        DEBUG_EXPECT_SEGFAULT(false);

        /* don't remove WRITE_BARRIER, but add CARDS_SET */
        obj->stm_flags |= (GCFLAG_CARDS_SET | GCFLAG_WB_EXECUTED);
        LIST_APPEND(STM_PSEGMENT->old_objects_with_cards_set, obj);
    } else {
        /* called if WB_EXECUTED is set or this is the first time
           for this obj: */

        /* add it to the GC list for minor collections */
        LIST_APPEND(STM_PSEGMENT->objects_pointing_to_nursery, obj);

        if (obj->stm_flags & GCFLAG_CARDS_SET) {
            assert(obj->stm_flags & GCFLAG_WB_EXECUTED);

            /* this is not the first_call to the WB for this obj,
               we executed the above then-part before.
               if we clear this flag, we have to add all the other
               bk slices we didn't add yet */
            make_bk_slices(obj,
                           false,       /* first_call */
                           -1,          /* index: whole obj */
                           true);       /* do_missing_cards */

        } else if (!(obj->stm_flags & GCFLAG_WB_EXECUTED)) {
            /* first and only time we enter here: */
            make_bk_slices(obj,
                           true,        /* first_call */
                           -1,          /* index: whole obj */
                           false);      /* do_missing_cards */
        }

        DEBUG_EXPECT_SEGFAULT(false);
        /* remove the WRITE_BARRIER flag and add WB_EXECUTED */
        obj->stm_flags &= ~(GCFLAG_WRITE_BARRIER | GCFLAG_CARDS_SET);
        obj->stm_flags |= GCFLAG_WB_EXECUTED;
    }

    DEBUG_EXPECT_SEGFAULT(true);
}


void _stm_write_slowpath_card(object_t *obj, uintptr_t index)
{
    dprintf_test(("write_slowpath_card(%p, %lu)\n",
                  obj, index));

    /* If CARDS_SET is not set so far, issue a normal write barrier.
       If the object is large enough, ask it to set up the object for
       card marking instead. */
    if (!(obj->stm_flags & GCFLAG_CARDS_SET)) {
        bool mark_card = obj_should_use_cards(STM_SEGMENT->segment_base, obj);
        write_slowpath_common(obj, mark_card);
        if (!mark_card)
            return;
    }

    assert(obj_should_use_cards(STM_SEGMENT->segment_base, obj));
    dprintf_test(("write_slowpath_card %p -> index:%lu\n",
                  obj, index));

    /* We reach this point if we have to mark the card. */
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);
    assert(obj->stm_flags & GCFLAG_CARDS_SET);
    assert(!is_small_uniform(obj)); /* not supported/tested */

#ifndef NDEBUG
    struct object_s *realobj = (struct object_s *)
        REAL_ADDRESS(STM_SEGMENT->segment_base, obj);
    size_t size = stmcb_size_rounded_up(realobj);
    /* we need at least one read marker in addition to the STM-reserved object
       write-lock */
    assert(size >= 32);
    /* the 'index' must be in range(length-of-obj), but we don't have
       a direct way to know the length.  We know that it is smaller
       than the size in bytes. */
    assert(index < size);
    /* this object was allocated with allocate_outside_nursery_large(),
       which returns addresses aligned to 16 bytes */
    assert((((uintptr_t)obj) & 15) == 0);
#endif

    /* Write into the card's lock.  This is used by the next minor
       collection to know what parts of the big object may have changed.
       We already own the object here or it is an overflow obj. */
    stm_read_marker_t *card = (stm_read_marker_t *)(((uintptr_t)obj) >> 4);
    card += get_index_to_card_index(index);

    if (!IS_OVERFLOW_OBJ(STM_PSEGMENT, obj)
        && !(card->rm == CARD_MARKED
             || card->rm == STM_SEGMENT->transaction_read_version)) {
        /* need to do the backup slice of the card */
        make_bk_slices(obj,
                       false,       /* first_call */
                       index,       /* index: only 1 card */
                       false);      /* do_missing_cards */
    }
    card->rm = CARD_MARKED;

    dprintf(("mark %p index %lu, card:%lu with %d\n",
             obj, index, get_index_to_card_index(index), CARD_MARKED));
}

__attribute__((flatten))
void _stm_write_slowpath(object_t *obj) {
    write_slowpath_common(obj,  /* mark_card */ false);
}


static void reset_transaction_read_version(void)
{
    /* force-reset all read markers to 0 */

    char *readmarkers = REAL_ADDRESS(STM_SEGMENT->segment_base,
                                     FIRST_READMARKER_PAGE * 4096UL);
    dprintf(("reset_transaction_read_version: %p %ld\n", readmarkers,
             (long)(NB_READMARKER_PAGES * 4096UL)));
    if (mmap(readmarkers, NB_READMARKER_PAGES * 4096UL,
             PROT_READ | PROT_WRITE,
             MAP_FIXED | MAP_PRIVATE | MAP_ANONYMOUS | MAP_NORESERVE, -1, 0) != readmarkers) {
        /* fall-back */
#if STM_TESTS
        stm_fatalerror("reset_transaction_read_version: %m");
#endif
        memset(readmarkers, 0, NB_READMARKER_PAGES * 4096UL);
    }
    STM_SEGMENT->transaction_read_version = 2;
    assert(STM_SEGMENT->transaction_read_version > _STM_CARD_MARKED);
}

static void reset_wb_executed_flags(void)
{
    dprintf(("reset_wb_executed_flags()\n"));
    struct list_s *list = STM_PSEGMENT->modified_old_objects;
    struct stm_undo_s *undo = (struct stm_undo_s *)list->items;
    struct stm_undo_s *end = (struct stm_undo_s *)(list->items + list->count);

    for (; undo < end; undo++) {
        if (undo->type == TYPE_POSITION_MARKER)
            continue;
        object_t *obj = undo->object;
        obj->stm_flags &= ~GCFLAG_WB_EXECUTED;
    }
}

static void readd_wb_executed_flags(void)
{
    dprintf(("readd_wb_executed_flags()\n"));
    struct list_s *list = STM_PSEGMENT->modified_old_objects;
    struct stm_undo_s *undo = (struct stm_undo_s *)list->items;
    struct stm_undo_s *end = (struct stm_undo_s *)(list->items + list->count);

    for (; undo < end; undo++) {
        if (undo->type == TYPE_POSITION_MARKER)
            continue;
        object_t *obj = undo->object;
        obj->stm_flags |= GCFLAG_WB_EXECUTED;
    }
}




static void _do_start_transaction(stm_thread_local_t *tl)
{
    assert(!_stm_in_transaction(tl));
    tl->wait_event_emitted = 0;

    acquire_thread_segment(tl);
    /* GS invalid before this point! */

    assert(STM_PSEGMENT->safe_point == SP_NO_TRANSACTION);
    assert(STM_PSEGMENT->transaction_state == TS_NONE);
    timing_event(tl, STM_TRANSACTION_START);
    STM_PSEGMENT->transaction_state = TS_REGULAR;
    STM_PSEGMENT->safe_point = SP_RUNNING;
#ifndef NDEBUG
    STM_PSEGMENT->running_pthread = pthread_self();
#endif
    STM_PSEGMENT->shadowstack_at_start_of_transaction = tl->shadowstack;
    STM_PSEGMENT->threadlocal_at_start_of_transaction = tl->thread_local_obj;
    STM_PSEGMENT->total_throw_away_nursery = 0;
    assert(tl->self_or_0_if_atomic == (intptr_t)tl);   /* not atomic */
    assert(STM_PSEGMENT->atomic_nesting_levels == 0);

    assert(list_is_empty(STM_PSEGMENT->modified_old_objects));
    assert(list_is_empty(STM_PSEGMENT->large_overflow_objects));
    assert(list_is_empty(STM_PSEGMENT->objects_pointing_to_nursery));
    assert(list_is_empty(STM_PSEGMENT->young_weakrefs));
    assert(tree_is_cleared(STM_PSEGMENT->young_outside_nursery));
    assert(tree_is_cleared(STM_PSEGMENT->nursery_objects_shadows));
    assert(tree_is_cleared(STM_PSEGMENT->callbacks_on_commit_and_abort[0]));
    assert(tree_is_cleared(STM_PSEGMENT->callbacks_on_commit_and_abort[1]));
    assert(list_is_empty(STM_PSEGMENT->young_objects_with_destructors));
    assert(STM_PSEGMENT->active_queues == NULL);
#ifndef NDEBUG
    /* this should not be used when objects_pointing_to_nursery == NULL */
    STM_PSEGMENT->position_markers_len_old = 99999999999999999L;
#endif

    check_nursery_at_transaction_start();

    if (tl->mem_reset_on_abort) {
        assert(!!tl->mem_stored_for_reset_on_abort);
        memcpy(tl->mem_stored_for_reset_on_abort, tl->mem_reset_on_abort,
               tl->mem_bytes_to_reset_on_abort);
    }


    /* Change read-version here, because if we do stm_validate in the
       safe-point below, we should not see our old reads from the last
       transaction. */
    uint8_t rv = STM_SEGMENT->transaction_read_version;
    if (rv < 0xff)   /* else, rare (maybe impossible?) case: we did already */
        rv++;        /* incr it but enter_safe_point_if_requested() aborted */
    STM_SEGMENT->transaction_read_version = rv;

    /* Warning: this safe-point may run light finalizers and register
       commit/abort callbacks if a major GC is triggered here */
    enter_safe_point_if_requested();
    dprintf(("> start_transaction\n"));

    s_mutex_unlock();   // XXX it's probably possible to not acquire this here

    if (UNLIKELY(rv == 0xff)) {
        reset_transaction_read_version();
    }

    stm_validate();
}

#ifdef STM_NO_AUTOMATIC_SETJMP
int did_abort = 0;
#endif

long _stm_start_transaction(stm_thread_local_t *tl)
{
    s_mutex_lock();
#ifdef STM_NO_AUTOMATIC_SETJMP
    long repeat_count = did_abort;    /* test/support.py */
    did_abort = 0;
#else
    long repeat_count = stm_rewind_jmp_setjmp(tl);
#endif
    if (repeat_count) {
        /* only if there was an abort, we need to reset the memory: */
        if (tl->mem_reset_on_abort)
            memcpy(tl->mem_reset_on_abort, tl->mem_stored_for_reset_on_abort,
                   tl->mem_bytes_to_reset_on_abort);
    }
    _do_start_transaction(tl);

    if (repeat_count == 0) {  /* else, 'nursery_mark' was already set
                                 in abort_data_structures_from_segment_num() */
        STM_SEGMENT->nursery_mark = ((stm_char *)_stm_nursery_start +
                                     stm_fill_mark_nursery_bytes);
    }
    return repeat_count;
}

#ifdef STM_NO_AUTOMATIC_SETJMP
void _test_run_abort(stm_thread_local_t *tl) __attribute__((noreturn));
int stm_is_inevitable(stm_thread_local_t *tl)
{
    assert(STM_SEGMENT->running_thread == tl);
    switch (STM_PSEGMENT->transaction_state) {
    case TS_REGULAR: return 0;
    case TS_INEVITABLE: return 1;
    default: abort();
    }
}
#endif

/************************************************************/

static void _finish_transaction(enum stm_event_e event)
{
    stm_thread_local_t *tl = STM_SEGMENT->running_thread;

    assert(_has_mutex());
    STM_PSEGMENT->safe_point = SP_NO_TRANSACTION;
    STM_PSEGMENT->transaction_state = TS_NONE;

    _verify_cards_cleared_in_all_lists(get_priv_segment(STM_SEGMENT->segment_num));
    list_clear(STM_PSEGMENT->objects_pointing_to_nursery);
    list_clear(STM_PSEGMENT->old_objects_with_cards_set);
    list_clear(STM_PSEGMENT->large_overflow_objects);
    if (tl != NULL)
        timing_event(tl, event);

    /* If somebody is waiting for us to reach a safe point, we simply
       signal it now and leave this transaction.  This should be enough
       for synchronize_all_threads() to retry and notice that we are
       no longer SP_RUNNING. */
    if (STM_SEGMENT->nursery_end != NURSERY_END)
        cond_signal(C_AT_SAFE_POINT);

    release_thread_segment(tl);
    /* cannot access STM_SEGMENT or STM_PSEGMENT from here ! */
}

static void check_all_write_barrier_flags(char *segbase, struct list_s *list)
{
#ifndef NDEBUG
    struct stm_undo_s *undo = (struct stm_undo_s *)list->items;
    struct stm_undo_s *end = (struct stm_undo_s *)(list->items + list->count);
    for (; undo < end; undo++) {
        if (undo->type == TYPE_POSITION_MARKER)
            continue;
        object_t *obj = undo->object;
        struct object_s *dst = (struct object_s*)REAL_ADDRESS(segbase, obj);
        assert(dst->stm_flags & GCFLAG_WRITE_BARRIER);
        assert(!(dst->stm_flags & GCFLAG_WB_EXECUTED));
    }
#endif
}

static void push_large_overflow_objects_to_other_segments(void)
{
    if (list_is_empty(STM_PSEGMENT->large_overflow_objects))
        return;

    /* XXX: also pushes small ones right now */
    acquire_privatization_lock(STM_SEGMENT->segment_num);
    LIST_FOREACH_R(STM_PSEGMENT->large_overflow_objects, object_t *,
        ({
            assert(!(item->stm_flags & GCFLAG_WB_EXECUTED));
            synchronize_object_enqueue(item);
        }));
    synchronize_objects_flush();
    release_privatization_lock(STM_SEGMENT->segment_num);

    /* we can as well clear the list here, since the
       objects are only useful if the commit succeeds. And
       we never do a major collection in-between.
       They should also survive any page privatization happening
       before the actual commit, since we always do a pagecopy
       in handle_segfault_in_page() that also copies
       unknown-to-the-segment/uncommitted things.
    */
    list_clear(STM_PSEGMENT->large_overflow_objects);
}


void _stm_commit_transaction(void)
{
    assert(STM_PSEGMENT->running_pthread == pthread_self());
    _core_commit_transaction(/*external=*/ false);
}

static void _core_commit_transaction(bool external)
{
    exec_local_finalizers();

    assert(!_has_mutex());
    assert(STM_PSEGMENT->safe_point == SP_RUNNING);
    assert(STM_PSEGMENT->transaction_state != TS_NONE);
    if (globally_unique_transaction) {
        stm_fatalerror("cannot commit between stm_stop_all_other_threads "
                       "and stm_resume_all_other_threads");
    }
    if (STM_PSEGMENT->atomic_nesting_levels > 0) {
        stm_fatalerror("cannot commit between stm_enable_atomic "
                       "and stm_disable_atomic");
    }
    assert(STM_SEGMENT->running_thread->self_or_0_if_atomic ==
           (intptr_t)(STM_SEGMENT->running_thread));
    assert(STM_SEGMENT->running_thread->wait_event_emitted == 0);

    dprintf(("> stm_commit_transaction(external=%d)\n", (int)external));
    minor_collection(/*commit=*/ true, external);
    if (!external && is_major_collection_requested()) {
        s_mutex_lock();
        if (is_major_collection_requested()) {   /* if still true */
            major_collection_with_mutex();
        }
        s_mutex_unlock();
    }

    push_large_overflow_objects_to_other_segments();
    /* push before validate. otherwise they are reachable too early */


    /* before releasing _stm_detached_inevitable_from_thread, perform
       the commit. Otherwise, the same thread whose (inev) transaction we try
       to commit here may start a new one in another segment *but* w/o
       the committed data from its previous inev transaction. (the
       stm_validate() at the start of a new transaction is happy even
       if there is an inevitable tx running) */
    bool was_inev = STM_PSEGMENT->transaction_state == TS_INEVITABLE;
    _validate_and_add_to_commit_log();

    if (external) {
        /* from this point on, unlink the original 'stm_thread_local_t *'
           from its segment.  Better do it as soon as possible, because
           other threads might be spin-looping, waiting for the -1 to
           disappear. */
        /* but first, emit commit-event of this thread: */
        timing_event(STM_SEGMENT->running_thread, STM_TRANSACTION_COMMIT);
        STM_SEGMENT->running_thread = NULL;
        stm_write_fence();
        assert(_stm_detached_inevitable_from_thread == -1);
        _stm_detached_inevitable_from_thread = 0;
    }


    if (!was_inev) {
        assert(!external);
        stm_rewind_jmp_forget(STM_SEGMENT->running_thread);
    }

    commit_finalizers();

    /* XXX do we still need a s_mutex_lock() section here? */
    s_mutex_lock();

    /* update 'overflow_number' if needed */
    if (STM_PSEGMENT->overflow_number_has_been_used) {
        highest_overflow_number += GCFLAG_OVERFLOW_NUMBER_bit0;
        assert(highest_overflow_number !=        /* XXX else, overflow! */
               (uint32_t)-GCFLAG_OVERFLOW_NUMBER_bit0);
        STM_PSEGMENT->overflow_number = highest_overflow_number;
        STM_PSEGMENT->overflow_number_has_been_used = false;
    }

    if (STM_PSEGMENT->active_queues)
        queues_deactivate_all(get_priv_segment(STM_SEGMENT->segment_num),
                              /*at_commit=*/true);

    invoke_and_clear_user_callbacks(0);   /* for commit */

    /* done */
    stm_thread_local_t *tl = STM_SEGMENT->running_thread;
    assert(external == (tl == NULL));
    _finish_transaction(STM_TRANSACTION_COMMIT);
    /* cannot access STM_SEGMENT or STM_PSEGMENT from here ! */

    s_mutex_unlock();

    /* between transactions, call finalizers. this will execute
       a transaction itself */
    if (tl != NULL)
        invoke_general_finalizers(tl);
}

static void undo_modifications_to_single_obj(int segment_num, object_t *obj)
{
    /* special function used for noconflict objs to reset all their
     * modifications and make them appear untouched in the current transaction.
     * I.e., reset modifications and remove from all lists. */

    struct stm_priv_segment_info_s *pseg = get_priv_segment(segment_num);

    reset_modified_from_backup_copies(segment_num, obj);

    /* reset read marker (must not be considered read either) */
    ((struct stm_read_marker_s *)
     (pseg->pub.segment_base + (((uintptr_t)obj) >> 4)))->rm = 0;

    /* reset possibly marked cards */
    if (get_page_status_in(segment_num, (uintptr_t)obj / 4096) == PAGE_ACCESSIBLE
        && obj_should_use_cards(pseg->pub.segment_base, obj)) {
        /* if header is not accessible, we didn't mark any cards */
        _reset_object_cards(pseg, obj, CARD_CLEAR, false, false);
    }

    /* remove from all other lists */
    LIST_FOREACH_R(pseg->old_objects_with_cards_set, object_t * /*item*/,
       {
           if (item == obj) {
               /* copy last element over this one (HACK) */
               _lst->count -= 1;
               _lst->items[_i] = _lst->items[_lst->count];
               break;
           }
       });
    LIST_FOREACH_R(pseg->objects_pointing_to_nursery, object_t * /*item*/,
       {
           if (item == obj) {
               /* copy last element over this one (HACK) */
               _lst->count -= 1;
               _lst->items[_i] = _lst->items[_lst->count];
               break;
           }
       });
}

static void reset_modified_from_backup_copies(int segment_num, object_t *only_obj)
{
#pragma push_macro("STM_PSEGMENT")
#pragma push_macro("STM_SEGMENT")
#undef STM_PSEGMENT
#undef STM_SEGMENT
    assert(modification_lock_check_wrlock(segment_num));

    /* WARNING: resetting the obj will remove the WB flag. Make sure you either
     * re-add it or remove it from lists where it was added based on the flag. */

    struct stm_priv_segment_info_s *pseg = get_priv_segment(segment_num);
    struct list_s *list = pseg->modified_old_objects;
    struct stm_undo_s *undo = (struct stm_undo_s *)list->items;
    struct stm_undo_s *end = (struct stm_undo_s *)(list->items + list->count);

    for (; undo < end; undo++) {
        if (undo->type == TYPE_POSITION_MARKER)
            continue;

        object_t *obj = undo->object;
        if (UNLIKELY(only_obj != NULL) && LIKELY(obj != only_obj))
            continue;

        char *dst = REAL_ADDRESS(pseg->pub.segment_base, obj);

        memcpy(dst + SLICE_OFFSET(undo->slice),
               undo->backup,
               SLICE_SIZE(undo->slice));

        dprintf(("reset_modified_from_backup_copies(%d): obj=%p off=%lu sz=%d bk=%p\n",
                 segment_num, obj, SLICE_OFFSET(undo->slice),
                 SLICE_SIZE(undo->slice), undo->backup));

        free_bk(undo);

        if (UNLIKELY(only_obj != NULL)) {
            assert(((struct object_s *)dst)->stm_flags & GCFLAG_NO_CONFLICT);

            /* copy last element over this one */
            end--;
            list->count -= 3;
            *undo = *end;
            /* to neutralise the increment for the next iter: */
            undo--;
        }
    }

    if (only_obj == NULL) {
        /* check that all objects have the GCFLAG_WRITE_BARRIER afterwards */
        check_all_write_barrier_flags(pseg->pub.segment_base, list);

        list_clear(list);
    }
#pragma pop_macro("STM_SEGMENT")
#pragma pop_macro("STM_PSEGMENT")
}

static void abort_data_structures_from_segment_num(int segment_num)
{
#pragma push_macro("STM_PSEGMENT")
#pragma push_macro("STM_SEGMENT")
#undef STM_PSEGMENT
#undef STM_SEGMENT
    struct stm_priv_segment_info_s *pseg = get_priv_segment(segment_num);

    switch (pseg->transaction_state) {
    case TS_REGULAR:
        break;
    case TS_INEVITABLE:
        stm_fatalerror("abort: transaction_state == TS_INEVITABLE");
    default:
        stm_fatalerror("abort: bad transaction_state == %d",
                       (int)pseg->transaction_state);
    }

    abort_finalizers(pseg);

    throw_away_nursery(pseg);

    /* clear CARD_MARKED on objs (don't care about CARD_MARKED_OLD) */
    LIST_FOREACH_R(pseg->old_objects_with_cards_set, object_t * /*item*/,
        {
            /* CARDS_SET may have already been lost because stm_validate()
               may call reset_modified_from_backup_copies() */
            _reset_object_cards(pseg, item, CARD_CLEAR, false, false);
        });

    acquire_modification_lock_wr(segment_num);
    reset_modified_from_backup_copies(segment_num, NULL);
    release_modification_lock_wr(segment_num);
    _verify_cards_cleared_in_all_lists(pseg);

    stm_thread_local_t *tl = pseg->pub.running_thread;
#ifdef STM_NO_AUTOMATIC_SETJMP
    /* In tests, we don't save and restore the shadowstack correctly.
       Be sure to not change items below shadowstack_at_start_of_transaction.
       There is no such restrictions in non-Python-based tests. */
    assert(tl->shadowstack >= pseg->shadowstack_at_start_of_transaction);
    tl->shadowstack = pseg->shadowstack_at_start_of_transaction;
#else
    /* NB. careful, this function might be called more than once to
       abort a given segment.  Make sure that
       stm_rewind_jmp_restore_shadowstack() is idempotent. */
    /* we need to do this here and not directly in rewind_longjmp() because
       that is called when we already released everything (safe point)
       and a concurrent major GC could mess things up. */
    if (tl->shadowstack != NULL)
        stm_rewind_jmp_restore_shadowstack(tl);
    assert(tl->shadowstack == pseg->shadowstack_at_start_of_transaction);
#endif
    tl->thread_local_obj = pseg->threadlocal_at_start_of_transaction;

    if (pseg->active_queues)
        queues_deactivate_all(pseg, /*at_commit=*/false);


    /* Set the next nursery_mark: first compute the value that
       nursery_mark must have had at the start of the aborted transaction */
    stm_char *old_mark =pseg->pub.nursery_mark + pseg->total_throw_away_nursery;

    /* This means that the limit, in term of bytes, was: */
    uintptr_t old_limit = old_mark - (stm_char *)_stm_nursery_start;

    /* If 'total_throw_away_nursery' is smaller than old_limit, use that */
    if (pseg->total_throw_away_nursery < old_limit)
        old_limit = pseg->total_throw_away_nursery;

    /* Now set the new limit to 90% of the old limit */
    pseg->pub.nursery_mark = ((stm_char *)_stm_nursery_start +
                              (uintptr_t)(old_limit * 0.9));

#ifdef STM_NO_AUTOMATIC_SETJMP
    did_abort = 1;
#endif

    list_clear(pseg->objects_pointing_to_nursery);
    list_clear(pseg->old_objects_with_cards_set);
    LIST_FOREACH_R(pseg->large_overflow_objects, uintptr_t /*item*/,
        {
            if (is_small_uniform((object_t*)item)) {
                //_stm_small_free()
            } else {
                _stm_large_free(stm_object_pages + item);
            }
        });
    list_clear(pseg->large_overflow_objects);
    list_clear(pseg->young_weakrefs);
#pragma pop_macro("STM_SEGMENT")
#pragma pop_macro("STM_PSEGMENT")
}


static stm_thread_local_t *abort_with_mutex_no_longjmp(void)
{
    assert(_has_mutex());
    dprintf(("~~~ ABORT\n"));

    assert(STM_PSEGMENT->running_pthread == pthread_self());

    abort_data_structures_from_segment_num(STM_SEGMENT->segment_num);

    stm_thread_local_t *tl = STM_SEGMENT->running_thread;
    tl->self_or_0_if_atomic = (intptr_t)tl;   /* clear the 'atomic' flag */
    STM_PSEGMENT->atomic_nesting_levels = 0;

    if (tl->mem_clear_on_abort)
        memset(tl->mem_clear_on_abort, 0, tl->mem_bytes_to_clear_on_abort);
    if (tl->mem_reset_on_abort) {
        /* temporarily set the memory of mem_reset_on_abort to zeros since in the
           case of vmprof, the old value is really wrong if we didn't do the longjmp
           back yet (that restores the C stack). We restore the memory in
           _stm_start_transaction() */
        memset(tl->mem_reset_on_abort, 0, tl->mem_bytes_to_reset_on_abort);
    }

    invoke_and_clear_user_callbacks(1);   /* for abort */

    if (is_abort(STM_SEGMENT->nursery_end)) {
        /* done aborting */
        STM_SEGMENT->nursery_end = pause_signalled ? NSE_SIGPAUSE
                                                   : NURSERY_END;
    }

    _finish_transaction(STM_TRANSACTION_ABORT);
    /* cannot access STM_SEGMENT or STM_PSEGMENT from here ! */

    return tl;
}

static void abort_with_mutex(void)
{
    stm_thread_local_t *tl = abort_with_mutex_no_longjmp();
    s_mutex_unlock();

    usleep(1);

#ifdef STM_NO_AUTOMATIC_SETJMP
    _test_run_abort(tl);
#else
    s_mutex_lock();
    stm_rewind_jmp_longjmp(tl);
#endif
}



#ifdef STM_NO_AUTOMATIC_SETJMP
void _test_run_abort(stm_thread_local_t *tl) __attribute__((noreturn));
#endif

void stm_abort_transaction(void)
{
    s_mutex_lock();
    abort_with_mutex();
}


void _stm_become_inevitable(const char *msg)
{
    int num_waits = 0;

    timing_become_inevitable();

 retry_from_start:
    assert(STM_PSEGMENT->transaction_state == TS_REGULAR);
    _stm_collectable_safe_point();

    if (msg != MSG_INEV_DONT_SLEEP) {
        dprintf(("become_inevitable: %s\n", msg));

        if (any_soon_finished_or_inevitable_thread_segment() &&
                num_waits <= NB_SEGMENTS) {
#if STM_TESTS                           /* for tests: another transaction */
            stm_abort_transaction();    /*   is already inevitable, abort */
#endif

            bool timed_out = false;

            s_mutex_lock();
            if (any_soon_finished_or_inevitable_thread_segment() &&
                    !safe_point_requested()) {

                /* wait until C_SEGMENT_FREE_OR_SAFE_POINT_REQ is signalled */
                EMIT_WAIT(STM_WAIT_OTHER_INEVITABLE);
                if (!cond_wait_timeout(C_SEGMENT_FREE_OR_SAFE_POINT_REQ,
                                       0.000054321))
                    timed_out = true;
            }
            s_mutex_unlock();

            if (timed_out) {
                /* try to detach another inevitable transaction, but
                   only after waiting a bit.  This is necessary to avoid
                   deadlocks in some situations, which are hopefully
                   not too common.  We don't want two threads constantly
                   detaching each other. */
                intptr_t detached = fetch_detached_transaction();
                if (detached != 0) {
                    EMIT_WAIT_DONE();
                    commit_fetched_detached_transaction(detached);
                }
            }
            else {
                num_waits++;
            }
            goto retry_from_start;
        }
        EMIT_WAIT_DONE();
        if (!_validate_and_turn_inevitable())
            goto retry_from_start;
    }
    else {
        if (!_validate_and_turn_inevitable())
            return;
    }

    /* There may be a concurrent commit of a detached Tx going on.
       Here, we may be right after the _validate_and_add_to_commit_log
       and before resetting _stm_detached_inevitable_from_thread to
       0. We have to wait for this to happen bc. otherwise, eg.
       _stm_detach_inevitable_transaction is not safe to do yet */
    while (_stm_detached_inevitable_from_thread == -1)
        stm_spin_loop();
    assert(_stm_detached_inevitable_from_thread == 0);

    soon_finished_or_inevitable_thread_segment();
    STM_PSEGMENT->transaction_state = TS_INEVITABLE;

    stm_rewind_jmp_forget(STM_SEGMENT->running_thread);
    invoke_and_clear_user_callbacks(0);   /* for commit */
}

#if 0
void stm_become_globally_unique_transaction(stm_thread_local_t *tl,
                                            const char *msg)
{
    stm_become_inevitable(tl, msg);

    s_mutex_lock();
    synchronize_all_threads(STOP_OTHERS_AND_BECOME_GLOBALLY_UNIQUE);
    s_mutex_unlock();
}
#endif

void stm_stop_all_other_threads(void)
{
    if (!stm_is_inevitable(STM_SEGMENT->running_thread))  /* may still abort */
        _stm_become_inevitable("stop_all_other_threads");

    s_mutex_lock();
    synchronize_all_threads(STOP_OTHERS_AND_BECOME_GLOBALLY_UNIQUE);
    s_mutex_unlock();
}

void stm_resume_all_other_threads(void)
{
    /* this calls 'committed_globally_unique_transaction()' even though
       we're not committing now.  It's a way to piggyback on the existing
       implementation for stm_become_globally_unique_transaction(). */
    s_mutex_lock();
    committed_globally_unique_transaction();
    s_mutex_unlock();
}



static inline void _synchronize_fragment(stm_char *frag, ssize_t frag_size)
{
    /* double-check that the result fits in one page */
    assert(frag_size > 0);
    assert(frag_size + ((uintptr_t)frag & 4095) <= 4096);

    /* XXX: is it possible to just add to the queue iff the pages
       of the fragment need syncing to other segments? (keep privatization
       lock until the "flush") */

    /* Enqueue this object (or fragemnt of object) */
    if (STM_PSEGMENT->sq_len == SYNC_QUEUE_SIZE)
        synchronize_objects_flush();
    STM_PSEGMENT->sq_fragments[STM_PSEGMENT->sq_len] = frag;
    STM_PSEGMENT->sq_fragsizes[STM_PSEGMENT->sq_len] = frag_size;
    ++STM_PSEGMENT->sq_len;
}



static void synchronize_object_enqueue(object_t *obj)
{
    assert(!_is_young(obj));
    assert(STM_PSEGMENT->privatization_lock);
    assert(obj->stm_flags & GCFLAG_WRITE_BARRIER);
    assert(!(obj->stm_flags & GCFLAG_WB_EXECUTED));
    assert(!(obj->stm_flags & GCFLAG_CARDS_SET));

    ssize_t obj_size = stmcb_size_rounded_up(
        (struct object_s *)REAL_ADDRESS(STM_SEGMENT->segment_base, obj));
    OPT_ASSERT(obj_size >= 16);

    if (LIKELY(is_small_uniform(obj))) {
        OPT_ASSERT(obj_size <= GC_LAST_SMALL_SIZE);
        _synchronize_fragment((stm_char *)obj, obj_size);
        return;
    }

    /* else, a more complicated case for large objects, to copy
       around data only within the needed pages */
    uintptr_t start = (uintptr_t)obj;
    uintptr_t end = start + obj_size;

    do {
        uintptr_t copy_up_to = (start + 4096) & ~4095;   /* end of page */
        if (copy_up_to >= end) {
            copy_up_to = end;        /* this is the last fragment */
        }
        uintptr_t copy_size = copy_up_to - start;

        /* double-check that the result fits in one page */
        assert(copy_size > 0);
        assert(copy_size + (start & 4095) <= 4096);

        _synchronize_fragment((stm_char *)start, copy_size);

        start = copy_up_to;
    } while (start != end);
}

static void synchronize_objects_flush(void)
{
    long j = STM_PSEGMENT->sq_len;
    if (j == 0)
        return;
    STM_PSEGMENT->sq_len = 0;

    dprintf(("synchronize_objects_flush(): %ld fragments\n", j));

    assert(STM_PSEGMENT->privatization_lock);
    DEBUG_EXPECT_SEGFAULT(false);

    long i, myself = STM_SEGMENT->segment_num;
    do {
        --j;
        stm_char *frag = STM_PSEGMENT->sq_fragments[j];
        uintptr_t page = ((uintptr_t)frag) / 4096UL;
        ssize_t frag_size = STM_PSEGMENT->sq_fragsizes[j];

        char *src = REAL_ADDRESS(STM_SEGMENT->segment_base, frag);
        for (i = 0; i < NB_SEGMENTS; i++) {
            if (i == myself)
                continue;

            if (get_page_status_in(i, page) != PAGE_NO_ACCESS) {
                /* shared or private, but never segfault */
                char *dst = REAL_ADDRESS(get_segment_base(i), frag);
                dprintf(("-> flush %p to seg %lu, sz=%lu\n", frag, i, frag_size));
                memcpy(dst, src, frag_size);
            }
        }
    } while (j > 0);

    DEBUG_EXPECT_SEGFAULT(true);
}
