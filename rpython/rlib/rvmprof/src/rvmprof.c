#define _GNU_SOURCE 1


#ifdef RPYTHON_LL2CTYPES
   /* only for testing: ll2ctypes sets RPY_EXTERN from the command-line */
#  ifndef RPY_EXTERN
#    define RPY_EXTERN RPY_EXPORTED
#  endif
#  define RPY_EXPORTED  extern __attribute__((visibility("default")))
#  define VMPROF_ADDR_OF_TRAMPOLINE(addr)  0

#else

#  include "common_header.h"
#  include "rvmprof.h"
#  ifndef VMPROF_ADDR_OF_TRAMPOLINE
#   error "RPython program using rvmprof, but not calling vmprof_execute_code()"
#  endif

#endif


#include "vmprof_main.h"
