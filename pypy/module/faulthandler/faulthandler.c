#include "faulthandler.h"
#include <stdlib.h>
#include <stdio.h>
#include <signal.h>
#include <assert.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>
#include <sys/resource.h>
#include <math.h>

#ifdef RPYTHON_LL2CTYPES
#  include "../../../rpython/rlib/rvmprof/src/rvmprof.h"
#else
#  include "common_header.h"
#  include "structdef.h"
#  include "rvmprof.h"
#endif
#include "src/threadlocal.h"

#define MAX_FRAME_DEPTH   100
#define FRAME_DEPTH_N     RVMPROF_TRACEBACK_ESTIMATE_N(MAX_FRAME_DEPTH)


typedef struct sigaction _Py_sighandler_t;

typedef struct {
    const int signum;
    volatile int enabled;
    const char* name;
    _Py_sighandler_t previous;
} fault_handler_t;

static struct {
    int initialized;
    int enabled;
    volatile int fd, all_threads;
    volatile pypy_faulthandler_cb_t dump_traceback;
} fatal_error;

static stack_t stack;


static fault_handler_t faulthandler_handlers[] = {
#ifdef SIGBUS
    {SIGBUS, 0, "Bus error", },
#endif
#ifdef SIGILL
    {SIGILL, 0, "Illegal instruction", },
#endif
    {SIGFPE, 0, "Floating point exception", },
    {SIGABRT, 0, "Aborted", },
    /* define SIGSEGV at the end to make it the default choice if searching the
       handler fails in faulthandler_fatal_error() */
    {SIGSEGV, 0, "Segmentation fault", }
};
static const int faulthandler_nsignals =
    sizeof(faulthandler_handlers) / sizeof(fault_handler_t);

RPY_EXTERN
void pypy_faulthandler_write(int fd, const char *str)
{
    (void)write(fd, str, strlen(str));
}

RPY_EXTERN
void pypy_faulthandler_write_int(int fd, long value)
{
    char buf[48];
    sprintf(buf, "%ld", value);
    pypy_faulthandler_write(fd, buf);
}


RPY_EXTERN
void pypy_faulthandler_dump_traceback(int fd, int all_threads,
                                      void *ucontext)
{
    pypy_faulthandler_cb_t fn;
    intptr_t array_p[FRAME_DEPTH_N], array_length;

    fn = fatal_error.dump_traceback;
    if (!fn)
        return;

#ifndef RPYTHON_LL2CTYPES
    if (all_threads && _RPython_ThreadLocals_AcquireTimeout(10000) == 0) {
        /* This is known not to be perfectly safe against segfaults if we
           don't hold the GIL ourselves.  Too bad.  I suspect that CPython
           has issues there too.
        */
        struct pypy_threadlocal_s *my, *p;
        int blankline = 0;
        char buf[40];

        my = (struct pypy_threadlocal_s *)_RPy_ThreadLocals_Get();
        p = _RPython_ThreadLocals_Head();
        p = _RPython_ThreadLocals_Enum(p);
        while (p != NULL) {
            if (blankline)
                pypy_faulthandler_write(fd, "\n");
            blankline = 1;

            pypy_faulthandler_write(fd, my == p ? "Current thread" : "Thread");
            sprintf(buf, " 0x%lx", (unsigned long)p->thread_ident);
            pypy_faulthandler_write(fd, buf);
            pypy_faulthandler_write(fd, " (most recent call first):\n");

            array_length = vmprof_get_traceback(p->vmprof_tl_stack,
                                                my == p ? ucontext : NULL,
                                                array_p, FRAME_DEPTH_N);
            fn(fd, array_p, array_length);

            p = _RPython_ThreadLocals_Enum(p);
        }
        _RPython_ThreadLocals_Release();
    }
    else {
        pypy_faulthandler_write(fd, "Stack (most recent call first):\n");
        array_length = vmprof_get_traceback(NULL, ucontext,
                                            array_p, FRAME_DEPTH_N);
        fn(fd, array_p, array_length);
    }
#else
    pypy_faulthandler_write(fd, "(no traceback when untranslated)\n");
#endif
}

static void
faulthandler_dump_traceback(int fd, int all_threads, void *ucontext)
{
    static volatile int reentrant = 0;

    if (reentrant)
        return;
    reentrant = 1;
    pypy_faulthandler_dump_traceback(fd, all_threads, ucontext);
    reentrant = 0;
}


/* Handler for SIGSEGV, SIGFPE, SIGABRT, SIGBUS and SIGILL signals.

   Display the current Python traceback, restore the previous handler and call
   the previous handler.

   On Windows, don't explicitly call the previous handler, because the Windows
   signal handler would not be called (for an unknown reason). The execution of
   the program continues at faulthandler_fatal_error() exit, but the same
   instruction will raise the same fault (signal), and so the previous handler
   will be called.

   This function is signal-safe and should only call signal-safe functions. */

static void
faulthandler_fatal_error(int signum, siginfo_t *info, void *ucontext)
{
    int fd = fatal_error.fd;
    int i;
    fault_handler_t *handler = NULL;
    int save_errno = errno;

    for (i = 0; i < faulthandler_nsignals; i++) {
        handler = &faulthandler_handlers[i];
        if (handler->signum == signum)
            break;
    }
    /* If not found, we use the SIGSEGV handler (the last one in the list) */

    /* restore the previous handler */
    if (handler->enabled) {
        (void)sigaction(signum, &handler->previous, NULL);
        handler->enabled = 0;
    }

    pypy_faulthandler_write(fd, "Fatal Python error: ");
    pypy_faulthandler_write(fd, handler->name);
    pypy_faulthandler_write(fd, "\n\n");

    faulthandler_dump_traceback(fd, fatal_error.all_threads, ucontext);

    errno = save_errno;
#ifdef MS_WINDOWS
    if (signum == SIGSEGV) {
        /* don't explicitly call the previous handler for SIGSEGV in this signal
           handler, because the Windows signal handler would not be called */
        return;
    }
#endif
    /* call the previous signal handler: it is called immediately if we use
       sigaction() thanks to SA_NODEFER flag, otherwise it is deferred */
    raise(signum);
}


RPY_EXTERN
char *pypy_faulthandler_setup(pypy_faulthandler_cb_t dump_callback)
{
    if (fatal_error.initialized)
        return NULL;
    assert(!fatal_error.enabled);
    fatal_error.dump_traceback = dump_callback;

    /* Try to allocate an alternate stack for faulthandler() signal handler to
     * be able to allocate memory on the stack, even on a stack overflow. If it
     * fails, ignore the error. */
    stack.ss_flags = 0;
    stack.ss_size = SIGSTKSZ;
    stack.ss_sp = malloc(stack.ss_size);
    if (stack.ss_sp != NULL) {
        int err = sigaltstack(&stack, NULL);
        if (err) {
            free(stack.ss_sp);
            stack.ss_sp = NULL;
        }
    }

    fatal_error.fd = -1;
    fatal_error.initialized = 1;
    return NULL;
}

RPY_EXTERN
void pypy_faulthandler_teardown(void)
{
    if (fatal_error.initialized) {
        pypy_faulthandler_disable();
        fatal_error.initialized = 0;
        if (stack.ss_sp) {
            stack.ss_flags = SS_DISABLE;
            sigaltstack(&stack, NULL);
            free(stack.ss_sp);
            stack.ss_sp = NULL;
        }
    }
}

RPY_EXTERN
char *pypy_faulthandler_enable(int fd, int all_threads)
{
    /* Install the handler for fatal signals, faulthandler_fatal_error(). */
    int i;
    fatal_error.fd = fd;
    fatal_error.all_threads = all_threads;

    if (!fatal_error.enabled) {
        fatal_error.enabled = 1;

        for (i = 0; i < faulthandler_nsignals; i++) {
            int err;
            struct sigaction action;
            fault_handler_t *handler = &faulthandler_handlers[i];

            action.sa_sigaction = faulthandler_fatal_error;
            sigemptyset(&action.sa_mask);
            /* Do not prevent the signal from being received from within
               its own signal handler */
            action.sa_flags = SA_NODEFER | SA_SIGINFO;
            if (stack.ss_sp != NULL) {
                /* Call the signal handler on an alternate signal stack
                   provided by sigaltstack() */
                action.sa_flags |= SA_ONSTACK;
            }
            err = sigaction(handler->signum, &action, &handler->previous);
            if (err) {
                return strerror(errno);
            }
            handler->enabled = 1;
        }
    }
    return NULL;
}

RPY_EXTERN
void pypy_faulthandler_disable(void)
{
    int i;
    if (fatal_error.enabled) {
        fatal_error.enabled = 0;
        for (i = 0; i < faulthandler_nsignals; i++) {
            fault_handler_t *handler = &faulthandler_handlers[i];
            if (!handler->enabled)
                continue;
            (void)sigaction(handler->signum, &handler->previous, NULL);
            handler->enabled = 0;
        }
    }
    fatal_error.fd = -1;
}

RPY_EXTERN
int pypy_faulthandler_is_enabled(void)
{
    return fatal_error.enabled;
}


/* for tests... */

static void
faulthandler_suppress_crash_report(void)
{
#ifdef MS_WINDOWS
    UINT mode;

    /* Configure Windows to not display the Windows Error Reporting dialog */
    mode = SetErrorMode(SEM_NOGPFAULTERRORBOX);
    SetErrorMode(mode | SEM_NOGPFAULTERRORBOX);
#endif

#ifndef MS_WINDOWS
    struct rlimit rl;

    /* Disable creation of core dump */
    if (getrlimit(RLIMIT_CORE, &rl) != 0) {
        rl.rlim_cur = 0;
        setrlimit(RLIMIT_CORE, &rl);
    }
#endif

#ifdef _MSC_VER
    /* Visual Studio: configure abort() to not display an error message nor
       open a popup asking to report the fault. */
    _set_abort_behavior(0, _WRITE_ABORT_MSG | _CALL_REPORTFAULT);
#endif
}

RPY_EXTERN
int pypy_faulthandler_read_null(void)
{
    int *volatile x;

    faulthandler_suppress_crash_report();
    x = NULL;
    return *x;
}

RPY_EXTERN
void pypy_faulthandler_sigsegv(void)
{
    faulthandler_suppress_crash_report();
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

RPY_EXTERN
int pypy_faulthandler_sigfpe(void)
{
    /* Do an integer division by zero: raise a SIGFPE on Intel CPU, but not on
       PowerPC. Use volatile to disable compile-time optimizations. */
    volatile int x = 1, y = 0, z;
    faulthandler_suppress_crash_report();
    z = x / y;
    /* If the division by zero didn't raise a SIGFPE (e.g. on PowerPC),
       raise it manually. */
    raise(SIGFPE);
    /* This line is never reached, but we pretend to make something with z
       to silence a compiler warning. */
    return z;
}

RPY_EXTERN
void pypy_faulthandler_sigabrt(void)
{
    faulthandler_suppress_crash_report();
    abort();
}

static double fh_stack_overflow(double levels)
{
    if (levels > 2.5) {
        return (sqrt(fh_stack_overflow(levels - 1.0))
                + fh_stack_overflow(levels * 1e-10));
    }
    return 1e100 + levels;
}

RPY_EXTERN
double pypy_faulthandler_stackoverflow(double levels)
{
    faulthandler_suppress_crash_report();
    return fh_stack_overflow(levels);
}
