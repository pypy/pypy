#define _GNU_SOURCE 1

#ifdef RPYTHON_LL2CTYPES
   /* only for testing: ll2ctypes sets RPY_EXTERN from the command-line */

#else
#  include "common_header.h"
#  include "structdef.h"
#  include "src/threadlocal.h"
#  include "rvmprof.h"
#endif

#include "shared/vmprof_get_custom_offset.h"
#ifdef VMPROF_UNIX
#include "shared/vmprof_main.h"
#else
#include "shared/vmprof_main_win32.h"
#endif


void * g_symbol = 0;

int IS_VMPROF_EVAL(void * ptr)
{
#ifdef RPYTHON_LL2CTYPES
    return 0;
#else

    if (g_symbol == NULL) {
        g_symbol = dlsym(RTLD_GLOBAL, "__vmprof_eval_vmprof");
        if (g_symbol == NULL) {
            fprintf(stderr, "symbol __vmprof_eval_vmprof could not be found\n");
            exit(-1);
        }
    }

    return ptr == g_symbol;
#endif
}
