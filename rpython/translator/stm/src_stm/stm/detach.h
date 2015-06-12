/* Imported by rpython/translator/stm/import_stmgc.py */
static void setup_detach(void);
static intptr_t fetch_detached_transaction(void);
static void commit_fetched_detached_transaction(intptr_t old);
static void commit_detached_transaction_if_from(stm_thread_local_t *tl);
