/* Imported by rpython/translator/stm/import_stmgc.py */


static void setup_sync(void);
static void teardown_sync(void);

/* all synchronization is done via a mutex and a few condition variables */
enum cond_type_e {
    C_SEGMENT_FREE,
    C_AT_SAFE_POINT,
    C_REQUEST_REMOVED,
    C_INEVITABLE,
    C_ABORTED,
    C_TRANSACTION_DONE,
    _C_TOTAL
};
static void s_mutex_lock(void);
static void s_mutex_unlock(void);
static void cond_wait(enum cond_type_e);
static void cond_signal(enum cond_type_e);
static void cond_broadcast(enum cond_type_e);
#ifndef NDEBUG
static bool _has_mutex(void);
#endif
static void set_gs_register(char *value);

/* acquire and release one of the segments for running the given thread
   (must have the mutex acquired!) */
static bool acquire_thread_segment(stm_thread_local_t *tl);
static void release_thread_segment(stm_thread_local_t *tl);

static void wait_for_end_of_inevitable_transaction(bool can_abort);
static void synchronize_all_threads(void);
