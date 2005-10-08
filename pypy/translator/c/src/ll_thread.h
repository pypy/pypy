/************************************************************/
 /***  C header subsection: OS-level threads               ***/


/* The core comes from thread.h, which is included from g_prerequisite.h.
   The functions below are declared later (from g_include.h). */

/* this cannot be moved to thread_*.h because:
 *  - RPyRaiseSimpleException and PyExc_thread_error are not declared yet
 *  - the macro redefining LL_thread_newlock (produced by genc) is not defined
 *    yet
 */

#define RPyOpaque_SETUP_ThreadLock(lock, initially_locked)		\
        if (!RPyThreadLockInit(lock))					\
	        error = "Thread lock init error";			\
        else if ((initially_locked) && !RPyThreadAcquireLock(lock, 1))	\
		error = "Cannot acquire thread lock at init";


/* prototypes */

void LL_thread_newlock(struct RPyOpaque_ThreadLock *lock);
int LL_thread_acquirelock(struct RPyOpaque_ThreadLock *lock, int waitflag);
void LL_thread_releaselock(struct RPyOpaque_ThreadLock *lock);
long LL_thread_start(void *func, void *arg);
long LL_thread_get_ident(void);


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

void LL_thread_newlock(struct RPyOpaque_ThreadLock *lock)
{
	if (!RPyThreadLockInit(lock))
		RPyRaiseSimpleException(PyExc_thread_error, "out of resources");
}

int LL_thread_acquirelock(struct RPyOpaque_ThreadLock *lock, int waitflag)
{
	return RPyThreadAcquireLock(lock, waitflag);
}

void LL_thread_releaselock(struct RPyOpaque_ThreadLock *lock)
{
	/* XXX this code is only quasi-thread-safe because the GIL is held
	       across its whole execution! */

	/* Sanity check: the lock must be locked */
	if (RPyThreadAcquireLock(lock, 0)) {
		RPyThreadReleaseLock(lock);
		RPyRaiseSimpleException(PyExc_thread_error, "bad lock");
	}
	else {
		RPyThreadReleaseLock(lock);
	}
}

long LL_thread_start(void *func, void *arg)
{
	/* XXX func() should not raise exceptions */
	long ident = RPyThreadStart((void (*)(void*)) func, arg);
	if (ident == -1)
		RPyRaiseSimpleException(PyExc_thread_error,
					"can't start new thread");
	return ident;
}

long LL_thread_get_ident(void)
{
	return RPyThreadGetIdent();
}

#endif /* PYPY_NOT_MAIN_FILE */
