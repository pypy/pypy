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


#if defined(MS_WINDOWS)
#  include <stdio.h>
#  include <fcntl.h>
#  include <io.h>
#  include <Windows.h>
   typedef unsigned short ARGV_T;
#else
   typedef char ARGV_T;
#endif

#ifdef RPY_WITH_GIL
# include <src/thread.h>
# include <src/threadlocal.h>
#endif

#ifdef RPY_REVERSE_DEBUGGER
# include <src-revdb/revdb_include.h>
#endif

static char already_initialized_non_threadsafe;
static void mark_initialized_now() { already_initialized_non_threadsafe = 1; }

RPY_EXPORTED
int rpython_startup_code(void)
{
    if (already_initialized_non_threadsafe)
        return 67;

#ifdef RPY_WITH_GIL
    RPython_ThreadLocals_ProgramInit();
    RPyGilAcquire();
#endif
    RPython_StartupCode();
    mark_initialized_now();
#ifdef RPY_WITH_GIL
    RPyGilRelease();
#endif
    return 0;
}


RPY_EXTERN
int pypy_main_function(int argc, ARGV_T *argv[])
{
    char *errmsg;
    int i, exitcode;

#ifdef MS_WINDOWS
    _setmode(0, _O_BINARY);
    _setmode(1, _O_BINARY);
    _setmode(2, _O_BINARY);
#endif

#ifdef RPY_WITH_GIL
    /* Note that the GIL's mutexes are not automatically made; if the
       program starts threads, it needs to call rgil.gil_allocate().
       RPyGilAcquire() still works without that, but crash if it finds
       that it really needs to wait on a mutex. */
    RPython_ThreadLocals_ProgramInit();
    RPyGilAcquire();
#endif

    instrument_setup();

#ifdef RPY_REVERSE_DEBUGGER
#ifdef MS_WINDOWS
    errmsg = "revdb not supported on windows"
    goto error;
#endif
    rpy_reverse_db_setup(&argc, &argv);
#endif

#ifdef MS_WINDOWS
    /* Convert wchar_t argv into char */
    char **converted_argv = malloc(sizeof(char*) * (argc + 1));
    converted_argv[argc] = NULL;
    for (int i=0; i<argc; i++) {
        int wlen = wcslen(argv[i]);
        if (wlen < 1) {
            converted_argv[i] = malloc(1);
            converted_argv[i][0] = 0;
            continue;
        }
        int lchar = WideCharToMultiByte(CP_UTF8, 0, argv[i], wlen, NULL, 0, NULL, NULL);
        if (lchar == 0) {
            /* fprintf(stdout, "failed to convert argument %d\n", i); */
            errmsg = "failed to convert command line arguments to UTF-8";
            goto error;
        }
        converted_argv[i] = malloc(lchar + 1);

        converted_argv[i][0] = 0;
        int lchar2 = WideCharToMultiByte(CP_UTF8, 0, argv[i], wlen,
                     converted_argv[i], lchar, NULL, NULL);
        if ((lchar2 != lchar) || (lchar == 0)) {
            errmsg = "failed to convert command line arguments to UTF-8";
            goto error;
        }
        converted_argv[i][lchar] = 0;
    }
#else
    /* this message does no longer apply to win64 :-) */
    if (sizeof(void*) != SIZEOF_LONG) {
        errmsg = "only support platforms where sizeof(void*) == sizeof(long),"
                 " for now";
        goto error;
    }
    char **converted_argv = argv;
#endif

    RPython_StartupCode();
    mark_initialized_now();

#ifndef RPY_REVERSE_DEBUGGER
    exitcode = STANDALONE_ENTRY_POINT(argc, converted_argv);
#else
    exitcode = rpy_reverse_db_main(STANDALONE_ENTRY_POINT, argc, argv);
#endif

    pypy_debug_alloc_results();

    if (RPyExceptionOccurred()) {
        /* print the RPython traceback */
        pypy_debug_catch_fatal_exception();
    }

    pypy_malloc_counters_results();
    pypy_print_field_stats();

#ifdef RPY_WITH_GIL
    RPyGilRelease();
#endif

    return exitcode;

 memory_out:
    errmsg = "out of memory";
 error:
    fprintf(stderr, "Fatal error during initialization: %s\n", errmsg);
    abort();
    return 1;
}

int PYPY_MAIN_FUNCTION(int argc, ARGV_T *argv[])
{
#ifdef PYPY_X86_CHECK_SSE2_DEFINED
    pypy_x86_check_sse2();
#endif
    return pypy_main_function(argc, argv);
}

#endif  /* PYPY_STANDALONE */
