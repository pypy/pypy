//#define USING_THREADED_BOEHM

#ifdef USING_THREADED_BOEHM

#define GC_REDIRECT_TO_LOCAL 1
#include <gc_local_alloc.h>

#else

#include <gc.h>

#endif

#define USING_BOEHM_GC

char *pypy_malloc(unsigned int size) {
  return GC_MALLOC(size);
}

char *pypy_malloc_atomic(unsigned int size) {
  return GC_MALLOC_ATOMIC(size);
}

extern GC_all_interior_pointers;
  char *RPython_StartupCode() {
  GC_all_interior_pointers = 0;
  GC_init();
  return LLVM_RPython_StartupCode();
}
