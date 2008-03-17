
/* some ifdefs from CPython's signalmodule.c... */

#ifndef _PYPY_SIGNALS_H
#define _PYPY_SIGNALS_H

#include <stdlib.h>

#ifdef MS_WINDOWS
#include <process.h>
#endif

#include <signal.h>

#ifndef SIG_ERR
#define SIG_ERR ((PyOS_sighandler_t)(-1))
#endif

#if defined(PYOS_OS2) && !defined(PYCC_GCC)
#define NSIG 12
#include <process.h>
#endif

#ifndef NSIG
# if defined(_NSIG)
#  define NSIG _NSIG		/* For BSD/SysV */
# elif defined(_SIGMAX)
#  define NSIG (_SIGMAX + 1)	/* For QNX */
# elif defined(SIGMAX)
#  define NSIG (SIGMAX + 1)	/* For djgpp */
# else
#  define NSIG 64		/* Use a reasonable default value */
# endif
#endif

/************************************************************/

/* NOTE: at the moment this file is included by a hack in
   module/signal/interp_signal.py, only if one of the pypysig_*()
   functions is actually used in the RPython program. */


/* utilities to set a signal handler */
void pypysig_ignore(int signum);  /* signal will be ignored (SIG_IGN) */
void pypysig_default(int signum); /* signal will do default action (SIG_DFL) */
void pypysig_setflag(int signum); /* signal will set a flag which can be
                                     queried with pypysig_poll() */

/* utility to poll for signals that arrived */
int pypysig_poll(void);   /* => signum or -1 */

/************************************************************/
/* Implementation                                           */

#ifndef PYPY_NOT_MAIN_FILE

static volatile int pypysig_occurred;
static volatile int pypysig_flags[NSIG];

void pypysig_ignore(int signum)
{
#ifdef SA_RESTART
    /* assume sigaction exists */
    struct sigaction context;
    context.sa_handler = SIG_IGN;
    sigemptyset(&context.sa_mask);
    context.sa_flags = 0;
    sigaction(signum, &context, NULL);
#else
  signal(signum, SIG_IGN);
#endif
}

void pypysig_default(int signum)
{
#ifdef SA_RESTART
    /* assume sigaction exists */
    struct sigaction context;
    context.sa_handler = SIG_DFL;
    sigemptyset(&context.sa_mask);
    context.sa_flags = 0;
    sigaction(signum, &context, NULL);
#else
  signal(signum, SIG_DFL);
#endif
}

static void signal_setflag_handler(int signum)
{
  if (0 <= signum && signum < NSIG)
    pypysig_flags[signum] = 1;
  pypysig_occurred = 1;
}

void pypysig_setflag(int signum)
{
#ifdef SA_RESTART
    /* assume sigaction exists */
    struct sigaction context;
    context.sa_handler = signal_setflag_handler;
    sigemptyset(&context.sa_mask);
    context.sa_flags = 0;
    sigaction(signum, &context, NULL);
#else
  signal(signum, signal_setflag_handler);
#endif
}

int pypysig_poll(void)
{
  if (pypysig_occurred)
    {
      int i;
      pypysig_occurred = 0;
      for (i=0; i<NSIG; i++)
        if (pypysig_flags[i])
          {
            pypysig_flags[i] = 0;
            pypysig_occurred = 1;  /* maybe another signal is pending */
            return i;
          }
    }
  return -1;  /* no pending signal */
}

#endif

#endif
