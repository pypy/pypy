#include "faulthandler.h"
#include <stdlib.h>
#include <stdio.h>
#include <signal.h>
#include <assert.h>
#include <errno.h>
#include <string.h>
#include <unistd.h>


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
    void (*volatile dump_traceback)(void);
    int _current_fd;
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

static void
fh_write(int fd, const char *str)
{
    (void)write(fd, str, strlen(str));
}

RPY_EXTERN
void pypy_faulthandler_write(char *str)
{
    fh_write(fatal_error._current_fd, str);
}

RPY_EXTERN
void pypy_faulthandler_write_int(long x)
{
    char buf[32];
    sprintf(buf, "%ld", x);
    fh_write(fatal_error._current_fd, buf);
}


RPY_EXTERN
void pypy_faulthandler_dump_traceback(int fd, int all_threads)
{
    fatal_error._current_fd = fd;

    /* XXX 'all_threads' ignored */
    if (fatal_error.dump_traceback)
        fatal_error.dump_traceback();
}

void faulthandler_dump_traceback(int fd, int all_threads)
{
    static volatile int reentrant = 0;

    if (reentrant)
        return;
    reentrant = 1;
    pypy_faulthandler_dump_traceback(fd, all_threads);
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
faulthandler_fatal_error(int signum)
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

    fh_write(fd, "Fatal Python error: ");
    fh_write(fd, handler->name);
    fh_write(fd, "\n\n");

    faulthandler_dump_traceback(fd, fatal_error.all_threads);

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
char *pypy_faulthandler_setup(void dump_callback(void))
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

RPY_EXTERN
int pypy_faulthandler_read_null(void)
{
    int *volatile x;

    x = NULL;
    return *x;
}

#if 0
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
