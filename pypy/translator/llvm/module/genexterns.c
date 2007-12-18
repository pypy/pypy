#include <stdlib.h>

char *LLVM_RPython_StartupCode(void);


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

/* alignment for arena-based garbage collectors: the following line
   enforces an alignment of 8.  This number 8 is also hard-coded in
   database.py:repr_offset(). */
#define MEMORY_ALIGNMENT		8
long ROUND_UP_FOR_ALLOCATION(long x) {
  return (x + (MEMORY_ALIGNMENT-1)) & ~(MEMORY_ALIGNMENT-1);
}


char *RPython_StartupCode() {
  // is there any garbage collection / memory management initialisation
  __GC_STARTUP_CODE__

  return LLVM_RPython_StartupCode();
}

#ifdef ENTRY_POINT_DEFINED

int _argc;
char **_argv;

int _pypy_getargc() {
  return _argc;
}

char ** _pypy_getargv() {
  return _argv;
}

/* we still need to forward declare our entry point */
int __ENTRY_POINT__(void);

#include <stdio.h>

int main(int argc, char *argv[]) {
  int res;
  char *errmsg;
  errmsg = RPython_StartupCode();
  if (errmsg) {
    fprintf(stderr, "Fatal error during initialization: %s\n", errmsg);
    return 1;
  }

  _argc = argc;
  _argv = argv;

  res = __ENTRY_POINT__();
  return res;
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

