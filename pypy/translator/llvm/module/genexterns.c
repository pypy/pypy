#include <stdlib.h>

char *LLVM_RPython_StartupCode(void);

#define RPyRaiseSimpleException(exctype, errormsg) raise##exctype(errormsg);

// XXX abort() this is just to make tests pass.  actually it is a million times
// better than it was since it used to basically be a nooop.

// all of these will go away at some point

#define FAKE_ERROR(name) \
  int raisePyExc_##name(char *x) { \
    abort(); \
   }

#ifdef LL_NEED_STACK
  FAKE_ERROR(RuntimeError);
  #include "src/thread.h"
  #include "src/stack.h"
#endif


// raw malloc code
char *raw_malloc(long size) {
  return malloc(size);
}

void raw_free(void *ptr) {
  free(ptr);
}

void raw_memcopy(char *ptr1, char *ptr2, long size) {
  memcpy((void *) ptr2, (void *) ptr1, size);
}

void raw_memclear(void* ptr, long size) {
  memset(ptr, 0, size);
}

char *RPython_StartupCode() {
  // is there any garbage collection / memory management initialisation
  __GC_STARTUP_CODE__

  return LLVM_RPython_StartupCode();
}

#ifdef ENTRY_POINT_DEFINED

int _argc;
char **argv;

int _pypy_getargc() {
  return _argc;
}

char ** _pypy_getargv() {
  return _argv;
}

int main(int argc, char *argv[]) {
  char *errmsg = RPython_StartupCode();
  if (errmsg) {
    fprintf(stderr, "Fatal error during initialization: %s\n", errmsg);
    return 1;
  }

  return __ENTRY_POINT__();
}

#else

int ctypes_RPython_StartupCode() {

  char *errmsg = RPython_StartupCode();
  if (errmsg != NULL) {
    return 0;
  }
  
  __GC_SETUP_CODE__

  return 1;
}

#endif /* ENTRY_POINT_DEFINED */

