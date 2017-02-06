#define _GNU_SOURCE 1

#ifdef RPYTHON_LL2CTYPES
   /* only for testing: ll2ctypes sets RPY_EXTERN from the command-line */

static volatile int is_enabled = 0;

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
