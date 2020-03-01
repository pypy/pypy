/* Thread implementation */
#include "src/thread.h"

/* The following include is required by the Boehm GC, which apparently
 * crashes when pthread_create_thread() is not redefined to call a
 * Boehm wrapper function instead.  Ugly.
 */
#include "common_header.h"

/* We need anyway to have "common_header.h" in order to include "structdef.h",
 * which is needed for _rpygil_get_my_ident().  Bah.
 */
#include "structdef.h"


#ifdef _WIN32
#include "src/thread_nt.c"
#else
#include "src/thread_pthread.c"
#endif
