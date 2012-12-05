#ifndef __PYPY_THREAD_H
#define __PYPY_THREAD_H
#include <assert.h>

#ifdef _WIN32
#include "thread_nt.h"
#else

/* We should check if unistd.h defines _POSIX_THREADS, but sometimes
   it is not defined even though the system implements them as an
   external library (e.g. gnu pth in pthread emulation).  So we just
   always go ahead and use them, assuming they are supported on all
   platforms for which we care.  If not, do some detecting again.
*/
#include "thread_pthread.h"

#endif /* !_WIN32 */

long RPyGilAllocate(void);
long RPyGilYieldThread(void);
void RPyGilRelease(void);
void RPyGilAcquire(void);

#endif
