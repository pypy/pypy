/* Thread implementation */
#include "src/thread.h"

/* The following include is required by the Boehm GC, which apparently
 * crashes where pthread_create() is not redefined to call a Boehm
 * wrapper function instead.  Ugly.
 */
#include "common_header.h"

#ifdef _WIN32
#include "src/thread_nt.c"
#else
#include "src/thread_pthread.c"
#endif

