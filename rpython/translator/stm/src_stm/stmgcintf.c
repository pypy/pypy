/************************************************************/
/* This is not meant to be compiled stand-alone, but with all
   of PyPy's #defines and #includes prepended. */

__thread struct stm_thread_local_s stm_thread_local;

/* 0 = not initialized; 1 = normal mode; 2 or more = atomic mode */
__thread long pypy_stm_ready_atomic;
__thread uintptr_t pypy_stm_nursery_low_fill_mark;

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

static long pypy_transaction_length;


void pypy_stm_set_transaction_length(long percentage)
{
    /* the value '100' means 'use the default'.  Other values are
       interpreted proportionally, up to some maximum. */
    long low_fill_mark = LOW_FILL_MARK * percentage / 100;
    if (low_fill_mark > NURSERY_SIZE / 2)
        low_fill_mark = NURSERY_SIZE / 2;
    pypy_transaction_length = low_fill_mark;
}

void pypy_stm_setup(void)
{
    stm_setup();
    pypy_stm_register_thread_local();
    pypy_stm_ready_atomic = 1;
    pypy_stm_set_transaction_length(100);
    pypy_stm_start_inevitable_if_not_atomic();
}

long pypy_stm_enter_callback_call(void)
{
    if (pypy_stm_ready_atomic == 0) {
        /* first time we see this thread */
        int e = errno;
        pypy_stm_register_thread_local();
        errno = e;
        pypy_stm_ready_atomic = 1;
        pypy_stm_start_inevitable_if_not_atomic();
        return 1;
    }
    else {
        /* callback from C code, itself called from Python code */
        pypy_stm_start_inevitable_if_not_atomic();
        return 0;
    }
}

void pypy_stm_leave_callback_call(long token)
{
    if (token == 1) {
        /* if we're returning into foreign C code that was not itself
           called from Python code, then we're ignoring the atomic
           status and committing anyway. */
        int e = errno;
        pypy_stm_ready_atomic = 1;
        stm_commit_transaction();
        pypy_stm_ready_atomic = 0;
        stm_unregister_thread_local(&stm_thread_local);
        errno = e;
    }
    else {
        pypy_stm_commit_if_not_atomic();
    }
}

void pypy_stm_perform_transaction(object_t *arg, int callback(object_t *, int))
{   /* must save roots around this call */
    stm_jmpbuf_t jmpbuf;
    long volatile v_counter = 0;
#ifndef NDEBUG
    object_t **volatile old_shadowstack = stm_thread_local.shadowstack;
#endif

    STM_PUSH_ROOT(stm_thread_local, arg);
    /*STM_PUSH_ROOT(END_MARKER_OFF); XXX redo this optimization */

    while (1) {

        if (pypy_stm_ready_atomic == 1) {
            stm_commit_transaction();
            STM_START_TRANSACTION(&stm_thread_local, jmpbuf);
            pypy_stm_ready_atomic = 1; /* reset after abort */
        }

        /* After setjmp(), the local variables v_* are preserved because they
         * are volatile.  The other variables are only declared here. */
        long counter, result;
        counter = v_counter;
        v_counter = counter + 1;

        /* If counter==0, initialize 'pypy_stm_nursery_low_fill_mark'
           from the configured length limit.  If counter>0, we did an
           abort, and we can now configure 'pypy_stm_nursery_low_fill_mark'
           to a value slightly smaller than the value at last abort.
        */
        if (stm_is_inevitable()) {
            pypy_stm_nursery_low_fill_mark = 0;
        }
        else {
            long limit;
            if (counter == 0) {
                limit = pypy_transaction_length;
            }
            else {
                limit = stm_thread_local.last_abort__bytes_in_nursery;
                limit -= (limit >> 4);
            }
            pypy_stm_nursery_low_fill_mark = _stm_nursery_start + limit;
        }

        /* invoke the callback in the new transaction */
        STM_POP_ROOT(stm_thread_local, arg);
        assert(old_shadowstack == stm_thread_local.shadowstack);
        STM_PUSH_ROOT(stm_thread_local, arg);
        result = callback(arg, counter);
        if (result <= 0)
            break;
        v_counter = 0;
    }

    if (STM_SEGMENT->jmpbuf_ptr == &jmpbuf) {
        /* we can't leave this function leaving a non-inevitable
           transaction whose jmpbuf points into this function
        */
        if (pypy_stm_ready_atomic == 1) {
            stm_commit_transaction();
            stm_start_inevitable_transaction(&stm_thread_local);
            pypy_stm_nursery_low_fill_mark = 0;
        }
        else {
            _stm_become_inevitable("perform_transaction left with atomic");
        }
    }

    //gcptr x = stm_pop_root();   /* pop the END_MARKER */
    //assert(x == END_MARKER_OFF || x == END_MARKER_ON);
    STM_POP_ROOT_RET(stm_thread_local);             /* pop the 'arg' */
    assert(old_shadowstack == stm_thread_local.shadowstack);
}
