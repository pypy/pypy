#define USING_THREADED_BOEHM = 1

#ifdef USING_THREADED_BOEHM

#define GC_REDIRECT_TO_LOCAL 1
#include <gc/gc_local_alloc.h>

#else

#include <gc.h>

#endif

#define USING_BOEHM_GC
