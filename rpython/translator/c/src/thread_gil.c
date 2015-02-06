
/* Idea:

   - "The GIL" is a composite concept.  There are two locks, and "the
     GIL is locked" when both are locked.

   - The first lock is a simple global variable 'rpy_fastgil'.  With
     shadowstack, we use the most portable definition: 0 means unlocked
     and != 0 means locked.  With asmgcc, 0 means unlocked but only 1
     means locked.  A different value means unlocked too, but the value
     is used by the JIT to contain the stack top for stack root scanning.

   - The second lock is a regular mutex.  In the fast path, it is never
     unlocked.  Remember that "the GIL is unlocked" means that either
     the first or the second lock is unlocked.  It should never be the
     case that both are unlocked at the same time.

   - Let's call "thread 1" the thread with the GIL.  Whenever it does an
     external function call, it sets 'rpy_fastgil' to 0 (unlocked).
     This is the cheapest way to release the GIL.  When it returns from
     the function call, this thread attempts to atomically change
     'rpy_fastgil' to 1.  In the common case where it works, thread 1
     has got the GIL back and so continues to run.

   - Say "thread 2" is eagerly waiting for thread 1 to become blocked in
     some long-running call.  Regularly, it checks if 'rpy_fastgil' is 0
     and tries to atomically change it to 1.  If it succeeds, it means
     that the GIL was not previously locked.  Thread 2 has now got the GIL.

   - If there are more than 2 threads, the rest is really sleeping by
     waiting on the 'mutex_gil_stealer' held by thread 2.

   - An additional mechanism is used for when thread 1 wants to
     explicitly yield the GIL to thread 2: it does so by releasing
     'mutex_gil' (which is otherwise not released) but keeping the
     value of 'rpy_fastgil' to 1.
*/

long rpy_fastgil = 1;
long rpy_waiting_threads = -42;    /* GIL not initialized */
static mutex1_t mutex_gil_stealer;
static mutex2_t mutex_gil;

void RPyGilAllocate(void)
{
    assert(RPY_FASTGIL_LOCKED(rpy_fastgil));
    mutex1_init(&mutex_gil_stealer);
    mutex2_init_locked(&mutex_gil);
    rpy_waiting_threads = 0;
}

void RPyGilAcquire(void)
{
    /* Acquires the GIL.
     */
    long old_fastgil = lock_test_and_set(&rpy_fastgil, 1);

    if (!RPY_FASTGIL_LOCKED(old_fastgil)) {
        /* The fastgil was not previously locked: success.
           'mutex_gil' should still be locked at this point.
        */
    }
    else {
        /* Otherwise, another thread is busy with the GIL. */

        /* Register me as one of the threads that is actively waiting
           for the GIL.  The number of such threads is found in
           rpy_waiting_threads. */
        assert(rpy_waiting_threads >= 0);
        atomic_increment(&rpy_waiting_threads);

        /* Enter the waiting queue from the end.  Assuming a roughly
           first-in-first-out order, this will nicely give the threads
           a round-robin chance.
        */
        mutex1_lock(&mutex_gil_stealer);
        mutex2_loop_start(&mutex_gil);

        /* We are now the stealer thread.  Steals! */
        while (1) {
            /* Sleep for one interval of time.  We may be woken up earlier
               if 'mutex_gil' is released.
            */
            if (mutex2_lock_timeout(&mutex_gil, 0.0001)) {   /* 0.1 ms... */
                /* We arrive here if 'mutex_gil' was recently released
                   and we just relocked it.
                 */
                old_fastgil = 0;
                break;
            }

            /* Busy-looping here.  Try to look again if 'rpy_fastgil' is
               released.
            */
            if (!RPY_FASTGIL_LOCKED(rpy_fastgil)) {
                old_fastgil = lock_test_and_set(&rpy_fastgil, 1);
                if (!RPY_FASTGIL_LOCKED(old_fastgil))
                    /* yes, got a non-held value!  Now we hold it. */
                    break;
            }
            /* Otherwise, loop back. */
        }
        atomic_decrement(&rpy_waiting_threads);
        mutex2_loop_stop(&mutex_gil);
        mutex1_unlock(&mutex_gil_stealer);
    }
    assert(RPY_FASTGIL_LOCKED(rpy_fastgil));

#ifdef PYPY_USE_ASMGCC
    if (old_fastgil != 0) {
        /* this case only occurs from the JIT compiler */
        struct pypy_ASM_FRAMEDATA_HEAD0 *new =
            (struct pypy_ASM_FRAMEDATA_HEAD0 *)old_fastgil;
        struct pypy_ASM_FRAMEDATA_HEAD0 *root = &pypy_g_ASM_FRAMEDATA_HEAD;
        struct pypy_ASM_FRAMEDATA_HEAD0 *next = root->as_next;
        new->as_next = next;
        new->as_prev = root;
        root->as_next = new;
        next->as_prev = new;
    }
#else
    assert(old_fastgil == 0);
#endif
}

long RPyGilYieldThread(void)
{
    /* can be called even before RPyGilAllocate(), but in this case,
       'rpy_waiting_threads' will be -42. */
    assert(RPY_FASTGIL_LOCKED(rpy_fastgil));
    if (rpy_waiting_threads <= 0)
        return 0;

    /* Explicitly release the 'mutex_gil'.
     */
    mutex2_unlock(&mutex_gil);

    /* Now nobody has got the GIL, because 'mutex_gil' is released (but
       rpy_fastgil is still locked).  Call RPyGilAcquire().  It will
       enqueue ourselves at the end of the 'mutex_gil_stealer' queue.
       If there is no other waiting thread, it will fall through both
       its mutex_lock() and mutex_lock_timeout() now.  But that's
       unlikely, because we tested above that 'rpy_waiting_threads > 0'.
     */
    RPyGilAcquire();
    return 1;
}

/********** for tests only **********/

/* These functions are usually defined as a macros RPyXyz() in thread.h
   which get translated into calls to _RpyXyz().  But for tests we need
   the real functions to exists in the library as well.
*/

#undef RPyGilRelease
RPY_EXTERN
void RPyGilRelease(void)
{
    /* Releases the GIL in order to do an external function call.
       We assume that the common case is that the function call is
       actually very short, and optimize accordingly.
    */
    _RPyGilRelease();
}

#undef RPyFetchFastGil
RPY_EXTERN
long *RPyFetchFastGil(void)
{
    return _RPyFetchFastGil();
}
