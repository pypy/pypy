/* Thread implementation */
#include "src/thread.h"

/* The following include is required by the Boehm GC, which apparently
 * crashes when pthread_create_thread() is not redefined to call a
 * Boehm wrapper function instead.  Ugly.
 *
 * It is also needed to see the definition of RPY_FASTGIL, if there is one.
 */
#include "common_header.h"

/* More ugliness follows... */
#ifdef RPY_FASTGIL
# if RPY_FASTGIL == 42    /* special value to mean "asmgcc" */
#  include "structdef.h"
#  include "forwarddecl.h"
# endif
#endif


#ifdef _WIN32
#include "src/thread_nt.c"
#else
#include "src/thread_pthread.c"
#endif

