/************************************************************/
 /***  C header subsection: OS-level threads               ***/


/* The core comes from thread.h, which is included from g_prerequisite.h.
   The functions below are declared later (from g_include.h). */

/* this cannot be moved to thread_*.h because:
 *  - RPyRaiseSimpleException and PyExc_thread_error are not declared yet
 *  - the macro redefining LL_thread_newlock (produced by genc) is not defined
 *    yet
 */
void LL_thread_newlock(struct RPyOpaque_ThreadLock *lock)
{
	if (!RPyThreadLockInit(lock))
		RPyRaiseSimpleException(PyExc_thread_error, "out of resources");
}
