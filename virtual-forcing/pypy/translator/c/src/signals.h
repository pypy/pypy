
/* some ifdefs from CPython's signalmodule.c... */

#ifndef _PYPY_SIGNALS_H
#define _PYPY_SIGNALS_H

#include <limits.h>

#ifndef LONG_MAX
#if SIZEOF_LONG == 4
#define LONG_MAX 0X7FFFFFFFL
#elif SIZEOF_LONG == 8
#define LONG_MAX 0X7FFFFFFFFFFFFFFFL
#else
#error "could not set LONG_MAX in pyport.h"
#endif
#endif

#ifndef LONG_MIN
#define LONG_MIN (-LONG_MAX-1)
#endif

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

/* When a signal is received, the high bit of pypysig_occurred is set.
   After all signals are processed by pypysig_poll(), the high bit is
   cleared again.  The variable is exposed and RPython code is free to
   use the other bits in any way. */
#define PENDING_SIGNAL_BIT   (LONG_MIN)   /* high bit */
extern long pypysig_occurred;

/* some C tricks to get/set the variable as efficiently as possible:
   use macros when compiling as a stand-alone program, but still
   export a function with the correct name for testing */
#undef pypysig_getaddr_occurred
void *pypysig_getaddr_occurred(void);
#ifndef PYPY_NOT_MAIN_FILE
void *pypysig_getaddr_occurred(void) { return (void *)(&pypysig_occurred); }
#endif
#define pypysig_getaddr_occurred()   ((void *)(&pypysig_occurred))

/************************************************************/
/* Implementation                                           */

#ifndef PYPY_NOT_MAIN_FILE


long pypysig_occurred;
static volatile long *pypysig_occurred_v = (volatile long *)&pypysig_occurred;
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
  /* the point of "*pypysig_occurred_v" instead of just "pypysig_occurred"
     is the volatile declaration */
  *pypysig_occurred_v |= PENDING_SIGNAL_BIT;
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
  /* the two commented out lines below are useful for performance in
     normal usage of pypysig_poll(); however, pypy/module/signal/ is
     not normal usage.  It only calls pypysig_poll() if the
     PENDING_SIGNAL_BIT is set, and it clears that bit first. */

/* if (pypysig_occurred & PENDING_SIGNAL_BIT) */
    {
      int i;
/*     pypysig_occurred &= ~PENDING_SIGNAL_BIT; */
      for (i=0; i<NSIG; i++)
        if (pypysig_flags[i])
          {
            pypysig_flags[i] = 0;
            /* maybe another signal is pending: */
            pypysig_occurred |= PENDING_SIGNAL_BIT;
            return i;
          }
    }
  return -1;  /* no pending signal */
}

#endif

#endif
