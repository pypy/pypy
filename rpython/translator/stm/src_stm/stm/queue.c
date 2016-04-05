/* Imported by rpython/translator/stm/import_stmgc.py */
typedef struct queue_entry_s {
    object_t *object;
    struct queue_entry_s *next;
} queue_entry_t;

typedef union stm_queue_segment_u {
    struct {
        /* a chained list of fresh entries that have been allocated and
           added to this queue during the current transaction.  If the
           transaction commits, these are moved to 'old_entries'. */
        queue_entry_t *added_in_this_transaction;

        /* a point inside the chained list above such that all items from
           this point are known to contain non-young objects, for GC */
        queue_entry_t *added_young_limit;

        /* a chained list of old entries that the current transaction
           popped.  only used if the transaction is not inevitable:
           if it aborts, these entries are added back to 'old_entries'. */
        queue_entry_t *old_objects_popped;

        /* a queue is active when either of the two chained lists
           above is not empty, until the transaction commits.  (this
           notion is per segment.)  this flag says that the queue is
           already in the tree STM_PSEGMENT->active_queues. */
        bool active;

        /* counts the number of put's done in this transaction, minus
           the number of task_done's */
        int64_t unfinished_tasks_in_this_transaction;
    };
    char pad[64];
} stm_queue_segment_t;


struct stm_queue_s {
    /* this structure is always allocated on a multiple of 64 bytes,
       and the 'segs' is an array of items 64 bytes each */
    stm_queue_segment_t segs[STM_NB_SEGMENTS];

    /* a chained list of old entries in the queue; modified only
       with the lock */
    queue_entry_t *old_entries;
    uint8_t old_entries_lock;

    /* total of 'unfinished_tasks_in_this_transaction' for all
       committed transactions */
    volatile int64_t unfinished_tasks;
};


stm_queue_t *stm_queue_create(void)
{
    void *mem = NULL;
    int result = posix_memalign(&mem, 64, sizeof(stm_queue_t));
    assert(result == 0);
    (void)result;
    memset(mem, 0, sizeof(stm_queue_t));
    return (stm_queue_t *)mem;
}

static void queue_free_entries(queue_entry_t *lst)
{
    while (lst != NULL) {
        queue_entry_t *next = lst->next;
        free(lst);
        lst = next;
    }
}

void stm_queue_free(stm_queue_t *queue)
{
    long i;
    dprintf(("free queue %p\n", queue));
    for (i = 0; i < STM_NB_SEGMENTS; i++) {
        stm_queue_segment_t *seg = &queue->segs[i];

        struct stm_priv_segment_info_s *pseg = get_priv_segment(i + 1);
        stm_spinlock_acquire(pseg->active_queues_lock);

        if (seg->active) {
            assert(pseg->active_queues != NULL);
            bool ok = tree_delete_item(pseg->active_queues, (uintptr_t)queue);
            assert(ok);
            (void)ok;
        }
        else {
            assert(!seg->added_in_this_transaction);
            assert(!seg->added_young_limit);
            assert(!seg->old_objects_popped);
        }

        stm_spinlock_release(pseg->active_queues_lock);

        queue_free_entries(seg->added_in_this_transaction);
        queue_free_entries(seg->old_objects_popped);
    }
    free(queue);
}

static inline void queue_lock_acquire(void)
{
    int num = STM_SEGMENT->segment_num;
    stm_spinlock_acquire(get_priv_segment(num)->active_queues_lock);
}
static inline void queue_lock_release(void)
{
    int num = STM_SEGMENT->segment_num;
    stm_spinlock_release(get_priv_segment(num)->active_queues_lock);
}

static void queue_activate(stm_queue_t *queue, stm_queue_segment_t *seg)
{
    assert(seg == &queue->segs[STM_SEGMENT->segment_num - 1]);

    if (!seg->active) {
        queue_lock_acquire();
        if (STM_PSEGMENT->active_queues == NULL)
            STM_PSEGMENT->active_queues = tree_create();
        tree_insert(STM_PSEGMENT->active_queues, (uintptr_t)queue, 0);
        assert(!seg->active);
        seg->active = true;
        dprintf(("activated queue %p\n", queue));
        queue_lock_release();
    }
}

static void queues_deactivate_all(struct stm_priv_segment_info_s *pseg,
                                  bool at_commit)
{
#pragma push_macro("STM_PSEGMENT")
#pragma push_macro("STM_SEGMENT")
#undef STM_PSEGMENT
#undef STM_SEGMENT
    stm_spinlock_acquire(pseg->active_queues_lock);

    bool added_any_old_entries = false;
    bool finished_more_tasks = false;
    wlog_t *item;
    TREE_LOOP_FORWARD(pseg->active_queues, item) {
        stm_queue_t *queue = (stm_queue_t *)item->addr;
        stm_queue_segment_t *seg = &queue->segs[pseg->pub.segment_num - 1];
        queue_entry_t *head, *freehead;

        if (at_commit) {
            int64_t d = seg->unfinished_tasks_in_this_transaction;
            if (d != 0) {
                finished_more_tasks |= (d < 0);
                __sync_add_and_fetch(&queue->unfinished_tasks, d);
            }
            head = seg->added_in_this_transaction;
            freehead = seg->old_objects_popped;
        }
        else {
            head = seg->old_objects_popped;
            freehead = seg->added_in_this_transaction;
        }

        /* forget the two lists of entries */
        seg->added_in_this_transaction = NULL;
        seg->added_young_limit = NULL;
        seg->old_objects_popped = NULL;
        seg->unfinished_tasks_in_this_transaction = 0;

        /* free the list of entries that must disappear */
        queue_free_entries(freehead);

        /* move the list of entries that must survive to 'old_entries' */
        if (head != NULL) {
            queue_entry_t *old;
            queue_entry_t *tail = head;
            assert(!_is_in_nursery(head->object));
            while (tail->next != NULL) {
                tail = tail->next;
                assert(!_is_in_nursery(tail->object));
            }
            dprintf(("items move to old_entries in queue %p\n", queue));

            stm_spinlock_acquire(queue->old_entries_lock);
            old = queue->old_entries;
            tail->next = old;
            queue->old_entries = head;
            stm_spinlock_release(queue->old_entries_lock);

            added_any_old_entries = true;
        }

        /* deactivate this queue */
        assert(seg->active);
        seg->active = false;
        dprintf(("deactivated queue %p\n", queue));

    } TREE_LOOP_END;

    tree_free(pseg->active_queues);
    pseg->active_queues = NULL;

    stm_spinlock_release(pseg->active_queues_lock);

    if (added_any_old_entries)
        cond_broadcast(C_QUEUE_OLD_ENTRIES);
    if (finished_more_tasks)
        cond_broadcast(C_QUEUE_FINISHED_MORE_TASKS);
#pragma pop_macro("STM_SEGMENT")
#pragma pop_macro("STM_PSEGMENT")
}

void stm_queue_put(object_t *qobj, stm_queue_t *queue, object_t *newitem)
{
    /* must be run in a transaction, but doesn't cause conflicts or
       delays or transaction breaks.  you need to push roots!
    */
    stm_queue_segment_t *seg = &queue->segs[STM_SEGMENT->segment_num - 1];
    queue_activate(queue, seg);

    queue_entry_t *entry = malloc(sizeof(queue_entry_t));
    assert(entry);
    entry->object = newitem;
    entry->next = seg->added_in_this_transaction;
    seg->added_in_this_transaction = entry;
    seg->unfinished_tasks_in_this_transaction++;
}

static void queue_check_entry(queue_entry_t *entry)
{
    assert(entry->object != NULL);
    assert(((TLPREFIX int *)entry->object)[1] != 0);   /* userdata != 0 */
}

object_t *stm_queue_get(object_t *qobj, stm_queue_t *queue, double timeout,
                        stm_thread_local_t *tl)
{
    /* if the queue is empty, this commits and waits outside a transaction.
       must not be called if the transaction is atomic!  never causes
       conflicts.  you need to push roots!
    */
    struct timespec t;
    bool t_ready = false;
    queue_entry_t *entry;
    object_t *result;
    stm_queue_segment_t *seg = &queue->segs[STM_SEGMENT->segment_num - 1];

    if (seg->added_in_this_transaction) {
        entry = seg->added_in_this_transaction;
        seg->added_in_this_transaction = entry->next;
        if (entry == seg->added_young_limit)
            seg->added_young_limit = entry->next;
        queue_check_entry(entry);
        result = entry->object;
        free(entry);
        return result;
    }

 retry:
    /* careful, STM_SEGMENT->segment_num may change here because
       we're starting new transactions below! */
    seg = &queue->segs[STM_SEGMENT->segment_num - 1];
    assert(!seg->added_in_this_transaction);

    /* can't easily use compare_and_swap here.  The issue is that
       if we do "compare_and_swap(&old_entry, entry, entry->next)",
       then we need to read entry->next, but a parallel thread
       could have grabbed the same entry and already freed it.
       More subtly, there is also an ABA problem: even if we
       read the correct entry->next, maybe a parallel thread
       can free and reuse this entry.  Then the compare_and_swap
       succeeds, but the value written is outdated nonsense.
    */
    stm_spinlock_acquire(queue->old_entries_lock);
    entry = queue->old_entries;
    if (entry != NULL)
        queue->old_entries = entry->next;
    stm_spinlock_release(queue->old_entries_lock);

    if (entry != NULL) {
        /* successfully popped the old 'entry'.  It remains in the
           'old_objects_popped' list for now.  From now on, this entry
           "belongs" to this segment and should never be read by
           another segment. */
        queue_activate(queue, seg);

        queue_check_entry(entry);
        assert(!_is_in_nursery(entry->object));

        entry->next = seg->old_objects_popped;
        seg->old_objects_popped = entry;
        return entry->object;
    }
    else {
        /* no pending entry, wait */
#if STM_TESTS
        assert(timeout == 0.0);   /* can't wait in the basic tests */
#endif
        if (timeout == 0.0) {
            if (!stm_is_inevitable(tl)) {
                STM_PUSH_ROOT(*tl, qobj);
                stm_become_inevitable(tl, "stm_queue_get");
                STM_POP_ROOT(*tl, qobj);
                goto retry;
            }
            else
                return NULL;
        }

        STM_PUSH_ROOT(*tl, qobj);
        _stm_commit_transaction();

        s_mutex_lock();
        while (queue->old_entries == NULL) {
            if (timeout < 0.0) {      /* no timeout */
                cond_wait(C_QUEUE_OLD_ENTRIES);
            }
            else {
                if (!t_ready) {
                    timespec_delay(&t, timeout);
                    t_ready = true;
                }
                if (!cond_wait_timespec(C_QUEUE_OLD_ENTRIES, &t)) {
                    timeout = 0.0;   /* timed out! */
                    break;
                }
            }
        }
        s_mutex_unlock();

        _stm_start_transaction(tl);
        STM_POP_ROOT(*tl, qobj);   /* 'queue' should stay alive until here */
        goto retry;
    }
}

void stm_queue_task_done(stm_queue_t *queue)
{
    stm_queue_segment_t *seg = &queue->segs[STM_SEGMENT->segment_num - 1];
    queue_activate(queue, seg);
    seg->unfinished_tasks_in_this_transaction--;
}

long stm_queue_join(object_t *qobj, stm_queue_t *queue, stm_thread_local_t *tl)
{
    int64_t result;

#if STM_TESTS
    result = queue->unfinished_tasks;   /* can't wait in tests */
    result += (queue->segs[STM_SEGMENT->segment_num - 1]
               .unfinished_tasks_in_this_transaction);
    return result;
#else
    STM_PUSH_ROOT(*tl, qobj);
    _stm_commit_transaction();

    s_mutex_lock();
    while ((result = queue->unfinished_tasks) > 0) {
        cond_wait(C_QUEUE_FINISHED_MORE_TASKS);
    }
    s_mutex_unlock();

    _stm_start_transaction(tl);
    STM_POP_ROOT(*tl, qobj);   /* 'queue' should stay alive until here */
#endif

    /* returns 0 for 'ok', or negative if there was more task_done()
       than put() so far */
    return result;
}

static void queue_trace_list(queue_entry_t *entry, void trace(object_t **),
                             queue_entry_t *stop_at)
{
    while (entry != stop_at) {
        trace(&entry->object);
        entry = entry->next;
    }
}

void stm_queue_tracefn(stm_queue_t *queue, void trace(object_t **))
{
    if (trace != TRACE_FOR_MINOR_COLLECTION) {
        long i;
        for (i = 0; i < STM_NB_SEGMENTS; i++) {
            stm_queue_segment_t *seg = &queue->segs[i];
            queue_trace_list(seg->old_objects_popped, trace, NULL);
            /* seg->added_in_this_transaction cannot be traced from here,
               because it typically contains overflow objects that need
               to be traced in the correct segment.  This is done with
               mark_visit_from_active_queues(). */
        }
        queue_trace_list(queue->old_entries, trace, NULL);
    }
    /* for minor collections, done differently.
       see collect_active_queues() below */
}

static void collect_active_queues(void)
{
    /* for minor collections */
    wlog_t *item;
    queue_lock_acquire();
    TREE_LOOP_FORWARD(STM_PSEGMENT->active_queues, item) {
        /* it is enough to trace the objects added in the current
           transaction.  All other objects reachable from the queue
           are old (or, worse, belong to a parallel thread and must
           not be traced).  Performance note: this is linear in the
           total number of active queues, but at least each queue that
           has not been touched for a while in a long transaction is
           handled very cheaply.
        */
        stm_queue_t *queue = (stm_queue_t *)item->addr;
        stm_queue_segment_t *seg = &queue->segs[STM_SEGMENT->segment_num - 1];
        if (seg->added_young_limit != seg->added_in_this_transaction) {
            dprintf(("minor collection trace queue %p\n", queue));
            queue_trace_list(seg->added_in_this_transaction,
                             &minor_trace_if_young,
                             seg->added_young_limit);
            seg->added_young_limit = seg->added_in_this_transaction;
        }
    } TREE_LOOP_END;
    queue_lock_release();
}

static void mark_visit_from_active_queues(void)
{
    /* for major collections */
    long j;
    for (j = 1; j < NB_SEGMENTS; j++) {
        struct stm_priv_segment_info_s *pseg = get_priv_segment(j);
        if (pseg->active_queues == NULL)
            continue;

        wlog_t *item;
        TREE_LOOP_FORWARD(pseg->active_queues, item) {
            stm_queue_t *queue = (stm_queue_t *)item->addr;
            dprintf(("mark visit from active queue %p\n", queue));

            stm_queue_segment_t *seg = &queue->segs[j - 1];
            queue_entry_t *entry = seg->added_in_this_transaction;

            while (entry != NULL) {
                mark_visit_possibly_overflow_object(entry->object, pseg);
                entry = entry->next;
            }
        } TREE_LOOP_END;
    }
}
