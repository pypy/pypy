#define _GNU_SOURCE 1
#include "common_header.h"

#ifndef VMPROF_ADDR_OF_TRAMPOLINE
#  error "RPython program using rvmprof, but not calling vmprof_execute_code()"
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
