/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_CORE_H_
# error "must be compiled via stmgc.c"
#endif


void stm_call_on_abort(stm_thread_local_t *tl,
                       void *key, void callback(void *))
{
    if (!_stm_in_transaction(tl)) {
        /* check that the current thread-local is really running a
           transaction, and do nothing otherwise. */
        return;
    }

    if (STM_PSEGMENT->transaction_state == TS_INEVITABLE) {
        /* ignore callbacks if we're in an inevitable transaction
           (which cannot abort) */
        return;
    }

    if (callback == NULL) {
        /* ignore the return value: unregistered keys can be
           "deleted" again */
        tree_delete_item(STM_PSEGMENT->callbacks_on_abort, (uintptr_t)key);
    }
    else {
        /* double-registering the same key will crash */
        tree_insert(STM_PSEGMENT->callbacks_on_abort,
                    (uintptr_t)key, (uintptr_t)callback);
    }
}

static void clear_callbacks_on_abort(void)
{
    if (!tree_is_cleared(STM_PSEGMENT->callbacks_on_abort))
        tree_clear(STM_PSEGMENT->callbacks_on_abort);
}

static void invoke_and_clear_callbacks_on_abort(void)
{
    wlog_t *item;
    struct tree_s *callbacks = STM_PSEGMENT->callbacks_on_abort;
    if (tree_is_cleared(callbacks))
        return;
    STM_PSEGMENT->callbacks_on_abort = tree_create();

    TREE_LOOP_FORWARD(*callbacks, item) {
        void *key = (void *)item->addr;
        void (*callback)(void *) = (void(*)(void *))item->val;
        assert(key != NULL);
        assert(callback != NULL);

        /* The callback may call stm_call_on_abort(key, NULL).  It is
           ignored, because 'callbacks_on_abort' was cleared already. */
        callback(key);

    } TREE_LOOP_END;

    tree_free(callbacks);
}
