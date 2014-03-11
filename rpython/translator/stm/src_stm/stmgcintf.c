/************************************************************/
/* This is not meant to be compiled stand-alone, but with all
   of PyPy's #defines and #includes prepended. */

__thread struct stm_thread_local_s stm_thread_local;

extern Signed pypy_stmcb_size_rounded_up(void*);
extern void pypy_stmcb_trace(void*, void(*)(void*));

inline ssize_t stmcb_size_rounded_up(struct object_s *obj) {
    ssize_t result = pypy_stmcb_size_rounded_up(obj);
    assert(result >= 16);
    assert((result & 7) == 0);
    return result;
}

inline void stmcb_trace(struct object_s *obj, void visit(object_t **)) {
    pypy_stmcb_trace(obj, (void(*)(void*))visit);
}


/************************************************************/
/* "include" the stmgc.c file here */
#include "src_stm/stmgc.c"

/************************************************************/


#define LOW_FILL_MARK   400000

stm_char *pypy_stm_nursery_low_fill_mark;


void pypy_stm_setup(void)
{
    stm_setup();
    stm_register_thread_local(&stm_thread_local);

    size_t low_fill_mark = LOW_FILL_MARK;
    if (low_fill_mark > NURSERY_SIZE / 2)
        low_fill_mark = NURSERY_SIZE / 2;
    pypy_stm_nursery_low_fill_mark = ((stm_char *)_stm_nursery_start) +
                                     low_fill_mark;

    stm_start_inevitable_transaction(&stm_thread_local);
}

long pypy_stm_enter_callback_call(void)
{
    long token = 0;

    if (stm_thread_local.shadowstack == NULL) {
        /* first time we see this thread */
        token = 1;
        stm_register_thread_local(&stm_thread_local);
    }
    stm_start_inevitable_transaction(&stm_thread_local);
    return token;
}

void pypy_stm_leave_callback_call(long token)
{
    stm_commit_transaction();
    if (token == 1) {
        stm_unregister_thread_local(&stm_thread_local);
        assert(stm_thread_local.shadowstack == NULL);
    }
}
