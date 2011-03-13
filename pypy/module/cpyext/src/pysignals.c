#include <Python.h>
#include <signal.h>

/* From pythonrun.c in the standard Python distribution */

/* Wrappers around sigaction() or signal(). */

/* It may seem odd that these functions do not interact with the rest of the
 * system (i.e.  their effects are not visible in the signal module) but
 * this is apparently intentional, CPython works the same way.  The signal
 * handlers defined in the signal module define what happens if the normal
 * Python signal handler is called.
 *
 * A bit whacky, but that's the way it is */

PyOS_sighandler_t
PyOS_getsig(int sig)
{
#ifdef SA_RESTART
        /* assume sigaction exists */
        struct sigaction context;
        if (sigaction(sig, NULL, &context) == -1)
                return SIG_ERR;
        return context.sa_handler;
#else
        PyOS_sighandler_t handler;
        handler = signal(sig, SIG_IGN);
        if (handler != SIG_ERR)
                signal(sig, handler);
        return handler;
#endif
}

PyOS_sighandler_t
PyOS_setsig(int sig, PyOS_sighandler_t handler)
{
#ifdef SA_RESTART
        /* assume sigaction exists */
        struct sigaction context, ocontext;
        context.sa_handler = handler;
        sigemptyset(&context.sa_mask);
        context.sa_flags = 0;
        if (sigaction(sig, &context, &ocontext) == -1)
                return SIG_ERR;
        return ocontext.sa_handler;
#else
        PyOS_sighandler_t oldhandler;
        oldhandler = signal(sig, handler);
#ifndef MS_WINDOWS
        /* should check if this exists */
        siginterrupt(sig, 1);
#endif
        return oldhandler;
#endif
}
