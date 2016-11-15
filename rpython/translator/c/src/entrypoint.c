#include "common_header.h"
#ifdef PYPY_STANDALONE
#include "structdef.h"
#include "forwarddecl.h"
#include "preimpl.h"
#include <src/entrypoint.h>
#include <src/commondefs.h>
#include <src/mem.h>
#include <src/instrument.h>
#include <src/rtyper.h>
#include <src/exception.h>
#include <src/debug_traceback.h>
#include <src/asm.h>

#include <stdlib.h>
#include <stdio.h>

#ifdef __GNUC__
/* Hack to prevent this function from being inlined.  Helps asmgcc
   because the main() function has often a different prologue/epilogue. */
RPY_EXTERN
int pypy_main_function(int argc, char *argv[]) __attribute__((__noinline__));
#endif

# ifdef PYPY_USE_ASMGCC
#  include "structdef.h"
#  include "forwarddecl.h"
# endif

#if defined(MS_WINDOWS)
#  include <stdio.h>
#  include <fcntl.h>
#  include <io.h>
#endif

#ifdef RPY_WITH_GIL
# include <src/thread.h>
#endif

RPY_EXPORTED
void rpython_startup_code(void)
{
#ifdef RPY_WITH_GIL
    RPyGilAcquire();
#endif
#ifdef PYPY_USE_ASMGCC
    pypy_g_rpython_rtyper_lltypesystem_rffi_StackCounter.sc_inst_stacks_counter++;
#endif
    pypy_asm_stack_bottom();
    RPython_StartupCode();
#ifdef PYPY_USE_ASMGCC
    pypy_g_rpython_rtyper_lltypesystem_rffi_StackCounter.sc_inst_stacks_counter--;
#endif
#ifdef RPY_WITH_GIL
    RPyGilRelease();
#endif
}


RPY_EXTERN
int pypy_main_function(int argc, char *argv[])
{
    char *errmsg;
    int i, exitcode;

#if defined(MS_WINDOWS)
    _setmode(0, _O_BINARY);
    _setmode(1, _O_BINARY);
    _setmode(2, _O_BINARY);
#endif

#ifdef RPY_WITH_GIL
    /* Note that the GIL's mutexes are not automatically made; if the
       program starts threads, it needs to call rgil.gil_allocate().
       RPyGilAcquire() still works without that, but crash if it finds
       that it really needs to wait on a mutex. */
    RPyGilAcquire();
#endif

#ifdef PYPY_USE_ASMGCC
    pypy_g_rpython_rtyper_lltypesystem_rffi_StackCounter.sc_inst_stacks_counter++;
#endif
    pypy_asm_stack_bottom();
    instrument_setup();

#ifndef MS_WINDOWS
    /* this message does no longer apply to win64 :-) */
    if (sizeof(void*) != SIZEOF_LONG) {
        errmsg = "only support platforms where sizeof(void*) == sizeof(long),"
                 " for now";
        goto error;
    }
#endif

    RPython_StartupCode();

#ifdef RPY_STM
    rewind_jmp_buf rjbuf;
    stm_rewind_jmp_enterframe(&stm_thread_local, &rjbuf);
#endif

    exitcode = STANDALONE_ENTRY_POINT(argc, argv);

    pypy_debug_alloc_results();

    if (RPyExceptionOccurred()) {
        /* print the RPython traceback */
        pypy_debug_catch_fatal_exception();
    }

    pypy_malloc_counters_results();

#ifdef RPY_WITH_GIL
    RPyGilRelease();
#endif

#ifdef RPY_STM
    stm_rewind_jmp_leaveframe(&stm_thread_local, &rjbuf);
#endif

    RPython_TeardownCode();
    return exitcode;

 memory_out:
    errmsg = "out of memory";
 error:
    fprintf(stderr, "Fatal error during initialization: %s\n", errmsg);
    abort();
    return 1;
}

int PYPY_MAIN_FUNCTION(int argc, char *argv[])
{
#ifdef PYPY_X86_CHECK_SSE2_DEFINED
    pypy_x86_check_sse2();
#endif
    return pypy_main_function(argc, argv);
}

#endif  /* PYPY_STANDALONE */
