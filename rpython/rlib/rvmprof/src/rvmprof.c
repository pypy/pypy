#define _GNU_SOURCE 1

#ifdef RPYTHON_LL2CTYPES
   /* only for testing: ll2ctypes sets RPY_EXTERN from the command-line */
#ifndef RPY_EXTERN
#define RPY_EXTERN RPY_EXPORTED
#endif
#ifdef _WIN32
#define RPY_EXPORTED __declspec(dllexport)
#else
#define RPY_EXPORTED  extern __attribute__((visibility("default")))
#endif

#else
#  include "common_header.h"
#  include "structdef.h"
#  include "src/threadlocal.h"
#  include "rvmprof.h"
#endif

#ifdef VMPROF_UNIX
#include "shared/vmprof_main.h"
#else
#include "shared/vmprof_main_win32.h"
#endif
