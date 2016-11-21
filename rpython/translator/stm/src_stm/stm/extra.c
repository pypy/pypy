/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
# include "core.h"  // silence flymake
#endif

static long register_callbacks(stm_thread_local_t *tl,
                               void *key, void callback(void *), long index)
{
    dprintf(("register_callbacks: tl=%p key=%p callback=%p index=%ld\n",
             tl, key, callback, index));
    if (!in_transaction(tl)) {
        /* check that the provided thread-local is really running a
           transaction, and do nothing otherwise. */
        dprintf(("  NOT IN TRANSACTION\n"));
        return -1;
    }
    /* The tl was only here to check that.  We're really using
       STM_PSEGMENT below, which is often but not always the
       segment corresponding to the tl.  One case where it's not
       the case is if this gets called from stmcb_light_finalizer()
       from abort_finalizers() from major collections or contention.
    */
    if (STM_PSEGMENT->transaction_state != TS_REGULAR) {
        /* ignore callbacks if we're in an inevitable transaction
           (which cannot abort) or no transaction at all in this segment */
        dprintf(("  STATE = %d\n", (int)STM_PSEGMENT->transaction_state));
        return -1;
    }

    struct tree_s *callbacks;
    callbacks = STM_PSEGMENT->callbacks_on_commit_and_abort[index];

    if (callback == NULL) {
        /* double-unregistering works, but return 0 */
        long res = tree_delete_item(callbacks, (uintptr_t)key);
        dprintf(("  DELETED %ld\n", res));
        return res;
    }
    else {
        /* double-registering the same key will crash */
        dprintf(("  INSERTING\n"));
        tree_insert(callbacks, (uintptr_t)key, (uintptr_t)callback);
        return 1;
    }
}


long stm_call_on_commit(stm_thread_local_t *tl,
                       void *key, void callback(void *))
{
    long result = register_callbacks(tl, key, callback, 0);
    if (result < 0 && callback != NULL) {
        /* no regular transaction running, invoke the callback
           immediately */
        dprintf(("stm_call_on_commit calls now: %p(%p)\n", callback, key));
        callback(key);
    }
    return result;
}

long stm_call_on_abort(stm_thread_local_t *tl,
                       void *key, void callback(void *))
{
    return register_callbacks(tl, key, callback, 1);
}

static void invoke_and_clear_user_callbacks(long index)
{
    struct tree_s *callbacks;

    /* clear the callbacks that we don't want to invoke at all */
    callbacks = STM_PSEGMENT->callbacks_on_commit_and_abort[1 - index];
    if (!tree_is_cleared(callbacks))
        tree_clear(callbacks);

    /* invoke the callbacks from the other group */
    callbacks = STM_PSEGMENT->callbacks_on_commit_and_abort[index];
    if (tree_is_cleared(callbacks))
        return;
    STM_PSEGMENT->callbacks_on_commit_and_abort[index] = tree_create();

    wlog_t *item;
    TREE_LOOP_FORWARD(callbacks, item) {
        void *key = (void *)item->addr;
        void (*callback)(void *) = (void(*)(void *))item->val;
        assert(key != NULL);
        assert(callback != NULL);

        /* The callback may call stm_call_on_abort(key, NULL)
           (so with callback==NULL).  It is ignored, because
           'callbacks_on_commit_and_abort' was cleared already. */
        dprintf(("invoke_and_clear_user_callbacks(%ld): %p(%p)\n",
                 index, callback, key));
        callback(key);

    } TREE_LOOP_END;

    tree_free(callbacks);
}
