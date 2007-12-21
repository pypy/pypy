// XXX use some form of "configure" script 
// disable this for boehm compiled without threading
#define USING_THREADED_BOEHM

#ifdef USING_THREADED_BOEHM

#define GC_LINUX_THREADS 1
#define GC_REDIRECT_TO_LOCAL 1
#define GC_I_HIDE_POINTERS 1
#include <gc_local_alloc.h>

#else

#define GC_I_HIDE_POINTERS 1
#include <gc.h>

#endif

#define USING_BOEHM_GC

char *pypy_malloc(long size) {
  return GC_MALLOC(size);
}

char *pypy_malloc_atomic(long size) {
  return GC_MALLOC_ATOMIC(size);
}

void pypy_gc__collect() {
  GC_gcollect();
  GC_invoke_finalizers();
}

void pypy_register_finalizer(void *whatever, void *proc) {
  GC_REGISTER_FINALIZER(whatever, (GC_finalization_proc)proc, NULL, NULL, NULL);
}

void pypy_disappearing_link(void *link, void *obj) {
  if (GC_base(obj) == NULL)
    ; /* 'obj' is probably a prebuilt object - it makes no */
      /* sense to register it then, and it crashes Boehm in */
      /* quite obscure ways */
  else
    GC_GENERAL_REGISTER_DISAPPEARING_LINK(link, obj);
}

extern GC_all_interior_pointers;

// startup specific code for boehm 
#define __GC_STARTUP_CODE__ \
  GC_all_interior_pointers = 0; \
  GC_init();


// Some malloced data is expected to be short-lived (exceptions).
// The follow is a hack to store such data in a ringbuffer.
// This yields an extremely good speedup in certain cases but
// fails badly (segfaults) when a reference to the data is kept
// around and used (much) later.

/* #define ringbufsize         1024 */
/* #define ringbufentry_maxsize  16 */

/* static  char    ringbufdata[ringbufsize + ringbufentry_maxsize]; */
/* static  long    ringbufindex = 0; */

/* char *pypy_malloc_ringbuffer(long size) { */
/*     if (size <= ringbufentry_maxsize) { //test expected to be optimized away during compile time */
/*         ringbufindex = (ringbufindex + ringbufentry_maxsize) & (ringbufsize - 1); */
/*         return &ringbufdata[ringbufindex]; */
/*     } else { */
/*         return GC_MALLOC(size); */
/*     } */
/* } */

/* char *pypy_malloc_atomic_ringbuffer(long size) { */
/*     if (size <= ringbufentry_maxsize) { //test expected to be optimized away during compile time */
/*         ringbufindex = (ringbufindex + ringbufentry_maxsize) & (ringbufsize - 1); */
/*         return &ringbufdata[ringbufindex]; */
/*     } else { */
/*         return GC_MALLOC_ATOMIC(size); */
/*     } */
/* } */

