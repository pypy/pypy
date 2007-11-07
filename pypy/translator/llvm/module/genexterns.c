
// append some genc files here manually from python
#ifdef _RPyListOfString_New     /*  :-(  */
#  define HAVE_RPY_LIST_OF_STRING
#endif

#include "c/src/thread.h"
#ifdef LL_NEED_MATH
  #include "c/src/ll_math.h"
#endif

#ifdef LL_NEED_STRTOD
  #include "c/src/ll_strtod.h"
#endif

#ifdef LL_NEED_STACK
  #include "c/src/stack.h"
#endif

// setup code for ThreadLock Opaque types
/*char *RPyOpaque_LLVM_SETUP_ThreadLock(struct RPyOpaque_ThreadLock *lock,
				      int initially_locked) {

  struct RPyOpaque_ThreadLock tmp = RPyOpaque_INITEXPR_ThreadLock;
  memcpy(lock, &tmp, sizeof(struct RPyOpaque_ThreadLock));

  if (!RPyThreadLockInit(lock)) {
    return "Thread lock init error";
  }
  if ((initially_locked) && !RPyThreadAcquireLock(lock, 1)) {
    return "Cannot acquire thread lock at init";
  }
  return NULL;
}
*/

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

char *LLVM_RPython_StartupCode();

char *RPython_StartupCode() {

  // is there any garbage collection / memory management initialisation
  __GC_STARTUP_CODE__

  return LLVM_RPython_StartupCode();
}

#ifdef ENTRY_POINT_DEFINED

int __ENTRY_POINT__(RPyListOfString *);

int main(int argc, char *argv[])
{
    char *errmsg;
    int i, exitcode;
    RPyListOfString *list;
    errmsg = RPython_StartupCode();
    if (errmsg) goto error;
    
    list = _RPyListOfString_New(argc);
    if (_RPyExceptionOccurred()) goto memory_out;
    for (i=0; i<argc; i++) {
      RPyString *s = RPyString_FromString(argv[i]);

      if (_RPyExceptionOccurred()) {
	goto memory_out;
      }

      _RPyListOfString_SetItem(list, i, s);
    }

    exitcode = __ENTRY_POINT__(list);

    if (_RPyExceptionOccurred()) {
      goto error; // XXX see genc
    }
    return exitcode;

 memory_out:
    errmsg = "out of memory";
 error:
    fprintf(stderr, "Fatal error during initialization: %s\n", errmsg);
    return 1;
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

