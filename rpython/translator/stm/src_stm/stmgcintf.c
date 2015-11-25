/************************************************************/
/* This is not meant to be compiled stand-alone, but with all
   of PyPy's #defines and #includes prepended. */

__thread
struct stm_thread_local_s stm_thread_local __attribute__((aligned(64))) = {0};


extern Signed pypy_stmcb_size_rounded_up(void*);
extern void pypy_stmcb_get_card_base_itemsize(void*, uintptr_t[]);
extern void pypy_stmcb_trace(void*, void(*)(void*));
extern void pypy_stmcb_trace_cards(void*, void(*)(void*), uintptr_t, uintptr_t);
extern Signed pypy_stmcb_obj_supports_cards(void*);
extern void *pypy_stmcb_fetch_finalizer(long);

inline ssize_t stmcb_size_rounded_up(struct object_s *obj) {
    ssize_t result = pypy_stmcb_size_rounded_up(obj);
    OPT_ASSERT(result >= 16);
    OPT_ASSERT((result & 7) == 0);
    return result;
}

inline void stmcb_get_card_base_itemsize(struct object_s *obj,
                                         uintptr_t offset_itemsize[2]) {
    pypy_stmcb_get_card_base_itemsize(obj, offset_itemsize);
}

inline void stmcb_trace(struct object_s *obj, void visit(object_t **)) {
    pypy_stmcb_trace(obj, (void(*)(void*))visit);
}

inline long stmcb_obj_supports_cards(struct object_s *obj) {
    return pypy_stmcb_obj_supports_cards(obj);
}

inline void stmcb_trace_cards(struct object_s *obj, void visit(object_t **),
                              uintptr_t start, uintptr_t stop) {
    pypy_stmcb_trace_cards(obj, (void(*)(void*))visit, start, stop);
}


/************************************************************/
/* "include" the stmgc.c file here */
#include "src_stm/stmgc.c"

/************************************************************/


void pypy_stm_setup(void)
{
    stm_setup();
    pypy_stm_setup_prebuilt();

    pypy_stm_register_thread_local();
    /* set transaction length to a very large limit until the first
       thread starts. stm_set_transaction_length() will then be called
       again by pypy. */
    stm_fill_mark_nursery_bytes = 1024 * NURSERY_SIZE;

    rewind_jmp_buf rjbuf;
    stm_rewind_jmp_enterframe(&stm_thread_local, &rjbuf);
    stm_enter_transactional_zone(&stm_thread_local);
    stm_become_inevitable(&stm_thread_local, "start-up");
    stm_rewind_jmp_leaveframe(&stm_thread_local, &rjbuf);

    pypy_stm_setup_prebuilt_hashtables();
}

void pypy_stm_set_transaction_length(double fraction)
{
    stm_fill_mark_nursery_bytes = (uintptr_t)(NURSERY_SIZE * fraction / 4);
}

void pypy_stm_teardown(void)
{
    pypy_stm_unregister_thread_local();
    /* stm_teardown() not called here for now; it's mostly for tests */
}

long pypy_stm_enter_callback_call(void *rjbuf)
{
    if (stm_thread_local.shadowstack_base == NULL) {
        /* first time we see this thread */
        int e = errno;
        pypy_stm_register_thread_local();
        stm_rewind_jmp_enterprepframe(&stm_thread_local,
                                      (rewind_jmp_buf *)rjbuf);
        errno = e;
        stm_enter_transactional_zone(&stm_thread_local);
        return 1;
    }
    else {
        /* callback from C code, itself called from Python code */
        stm_rewind_jmp_enterprepframe(&stm_thread_local,
                                      (rewind_jmp_buf *)rjbuf);
        stm_enter_transactional_zone(&stm_thread_local);
        return 0;
    }
}

void pypy_stm_leave_callback_call(void *rjbuf, long token)
{
    stm_leave_transactional_zone(&stm_thread_local);
    stm_rewind_jmp_leaveframe(&stm_thread_local, (rewind_jmp_buf *)rjbuf);

    if (token == 1) {
        /* if we're returning into foreign C code that was not itself
           called from Python code, then we're ignoring the atomic
           status and committing anyway. */
        int e = errno;
        pypy_stm_unregister_thread_local();
        errno = e;
    }
}

/*void _pypy_stm_become_inevitable(const char *msg)
{
    _pypy_stm_inev_state();
    if (msg == NULL) {
        msg = "return from JITted function";
    }
    _stm_become_inevitable(msg);
}*/

long _pypy_stm_count(void)
{
    static long value = 1;
    return __sync_fetch_and_add(&value, 1);
}
