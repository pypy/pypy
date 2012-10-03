/* Thread implementation */
#include "src/thread.h"

#ifdef _WIN32
#include "src/thread_nt.c"
#else
#include "src/thread_pthread.c"
#endif

