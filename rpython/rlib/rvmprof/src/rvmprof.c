#define _GNU_SOURCE 1


#if defined(RPY_EXTERN) && !defined(RPY_EXPORTED)
   /* only for testing: ll2ctypes sets RPY_EXTERN from the command-line */
#  define RPY_EXPORTED  extern __attribute__((visibility("default")))

#else

#  include "common_header.h"
#  include "rvmprof.h"
#  ifndef VMPROF_ADDR_OF_TRAMPOLINE
#   error "RPython program using rvmprof, but not calling vmprof_execute_code()"
#  endif

#endif


#include "rvmprof_getpc.h"
#include "rvmprof_base.h"
#include <dlfcn.h>


/************************************************************/

// functions copied from libunwind using dlopen

static int (*unw_get_reg)(unw_cursor_t*, int, unw_word_t*) = NULL;
static int (*unw_step)(unw_cursor_t*) = NULL;
static int (*unw_init_local)(unw_cursor_t *, unw_context_t *) = NULL;
static int (*unw_get_proc_info)(unw_cursor_t *, unw_proc_info_t *) = NULL;


RPY_EXTERN
char *rpython_vmprof_init(void)
{
    if (!unw_get_reg) {
        void *libhandle;

        if (!(libhandle = dlopen("libunwind.so", RTLD_LAZY | RTLD_LOCAL)))
            goto error;
        if (!(unw_get_reg = dlsym(libhandle, "_ULx86_64_get_reg")))
            goto error;
        if (!(unw_get_proc_info = dlsym(libhandle, "_ULx86_64_get_proc_info")))
            goto error;
        if (!(unw_init_local = dlsym(libhandle, "_ULx86_64_init_local")))
            goto error;
        if (!(unw_step = dlsym(libhandle, "_ULx86_64_step")))
            goto error;
    }
    return NULL;

 error:
    return dlerror();
}

/************************************************************/

static long volatile ignore_signals = 0;

RPY_EXTERN
void rpython_vmprof_ignore_signals(int ignored)
{
#ifndef _MSC_VER
    if (ignored)
        __sync_lock_test_and_set(&ignore_signals, 1);
    else
        __sync_lock_release(&ignore_signals);
#else
    _InterlockedExchange(&ignore_signals, (long)ignored);
#endif
}
