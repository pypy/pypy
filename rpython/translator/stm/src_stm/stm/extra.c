/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


static long register_callbacks(stm_thread_local_t *tl,
                               void *key, void callback(void *), long index)
{
    if (!_stm_in_transaction(tl)) {
        /* check that the current thread-local is really running a
           transaction, and do nothing otherwise. */
        return -1;
    }

    if (STM_PSEGMENT->transaction_state == TS_INEVITABLE) {
        /* ignore callbacks if we're in an inevitable transaction
           (which cannot abort) */
        return -1;
    }

    struct tree_s *callbacks;
    callbacks = STM_PSEGMENT->callbacks_on_commit_and_abort[index];

    if (callback == NULL) {
        /* double-unregistering works, but return 0 */
        return tree_delete_item(callbacks, (uintptr_t)key);
    }
    else {
        /* double-registering the same key will crash */
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
    TREE_LOOP_FORWARD(*callbacks, item) {
        void *key = (void *)item->addr;
        void (*callback)(void *) = (void(*)(void *))item->val;
        assert(key != NULL);
        assert(callback != NULL);

        /* The callback may call stm_call_on_abort(key, NULL).  It is ignored,
           because 'callbacks_on_commit_and_abort' was cleared already. */
        callback(key);

    } TREE_LOOP_END;

    tree_free(callbacks);
}
