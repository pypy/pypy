#include "faulthandler.h"
#include <stdlib.h>
#include <signal.h>
#include <assert.h>
#include <errno.h>


typedef struct sigaction _Py_sighandler_t;

typedef struct {
    int signum;
    int enabled;
    const char* name;
    _Py_sighandler_t previous;
    int all_threads;
} fault_handler_t;

static struct {
    int enabled;
    int fd, all_threads;
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
char *pypy_faulthandler_setup(void)
{
    assert(!fatal_error.enabled);

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
    return NULL;
}

RPY_EXTERN
void pypy_faulthandler_teardown(void)
{
    pypy_faulthandler_disable();
    free(stack.ss_sp);
    stack.ss_sp = NULL;
}

RPY_EXTERN
int pypy_faulthandler_enable(int fd, int all_threads)
{
    fatal_error.fd = fd;
    fatal_error.all_threads = all_threads;

    if (!fatal_error.enabled) {
        int i;

        fatal_error.enabled = 1;

        for (i = 0; i < faulthandler_nsignals; i++) {
            int err;
            struct sigaction action;
            fault_handler_t *handler = &faulthandler_handlers[i];

            action.sa_handler = faulthandler_fatal_error;
            sigemptyset(&action.sa_mask);
            /* Do not prevent the signal from being received from within
               its own signal handler */
            action.sa_flags = SA_NODEFER;
            if (stack.ss_sp != NULL) {
                /* Call the signal handler on an alternate signal stack
                   provided by sigaltstack() */
                action.sa_flags |= SA_ONSTACK;
            }
            err = sigaction(handler->signum, &action, &handler->previous);
            if (err) {
                return -1;
            }
            handler->enabled = 1;
        }
    }
    return 0;
}

RPY_EXTERN
void pypy_faulthandler_disable(void)
{
    if (fatal_error.enabled) {
        int i;

        fatal_error.enabled = 0;
        for (i = 0; i < faulthandler_nsignals; i++) {
            fault_handler_t *handler = &faulthandler_handlers[i];
            if (!handler->enabled)
                continue;
            (void)sigaction(handler->signum, &handler->previous, NULL);
            handler->enabled = 0;
        }
    }
}

RPY_EXTERN
int pypy_faulthandler_is_enabled(void)
{
    return fatal_error.enabled;
}


#if 0
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
#endif
