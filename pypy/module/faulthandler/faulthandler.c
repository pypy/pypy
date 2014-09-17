#include <stdlib.h>
#include "faulthandler.h"

int
pypy_faulthandler_read_null(void)
{
    volatile int *x;
    volatile int y;

    x = NULL;
    y = *x;
    return y;
}

void
pypy_faulthandler_sigsegv(void)
{
#if defined(MS_WINDOWS)
    /* For SIGSEGV, faulthandler_fatal_error() restores the previous signal
       handler and then gives back the execution flow to the program (without
       explicitly calling the previous error handler). In a normal case, the
       SIGSEGV was raised by the kernel because of a fault, and so if the
       program retries to execute the same instruction, the fault will be
       raised again.

       Here the fault is simulated by a fake SIGSEGV signal raised by the
       application. We have to raise SIGSEGV at lease twice: once for
       faulthandler_fatal_error(), and one more time for the previous signal
       handler. */
    while(1)
        raise(SIGSEGV);
#else
    raise(SIGSEGV);
#endif
}

int
pypy_faulthandler_sigfpe(void)
{
    /* Do an integer division by zero: raise a SIGFPE on Intel CPU, but not on
       PowerPC. Use volatile to disable compile-time optimizations. */
    volatile int x = 1, y = 0, z;
    z = x / y;
    /* If the division by zero didn't raise a SIGFPE (e.g. on PowerPC),
       raise it manually. */
    raise(SIGFPE);
    /* This line is never reached, but we pretend to make something with z
       to silence a compiler warning. */
    return z;
}

void
pypy_faulthandler_sigabrt()
{
#ifdef _MSC_VER
    /* Visual Studio: configure abort() to not display an error message nor
       open a popup asking to report the fault. */
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#endif
    abort();
}

#ifdef SIGBUS
void
pypy_faulthandler_sigbus(void)
{
    raise(SIGBUS);
}
#endif

#ifdef SIGILL
void
pypy_faulthandler_sigill(void)
{
    raise(SIGILL);
}
#endif
