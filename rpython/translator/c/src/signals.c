#include "src/signals.h"

#include <limits.h>
#include <stdlib.h>
#ifdef _WIN32
#include <process.h>
#include <io.h>
#else
#include <unistd.h>
#endif
#include <signal.h>


/* some ifdefs from CPython's signalmodule.c... */

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

struct pypysig_long_struct pypysig_counter = {0};
static char volatile pypysig_flags[NSIG] = {0};
static int volatile pypysig_occurred = 0;
/* pypysig_occurred is only an optimization: it tells if any
   pypysig_flags could be set. */
static int wakeup_fd = -1;
static int wakeup_with_nul_byte = 1;

#undef pypysig_getaddr_occurred
void *pypysig_getaddr_occurred(void)
{
    return (void *)(&pypysig_counter); 
}

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

void pypysig_pushback(int signum)
{
    if (0 <= signum && signum < NSIG)
      {
        pypysig_flags[signum] = 1;
        pypysig_occurred = 1;
        pypysig_counter.value = -1;
      }
}

static void signal_setflag_handler(int signum)
{
    pypysig_pushback(signum);

    if (wakeup_fd != -1) 
      {
#ifndef _WIN32
        ssize_t res;
#else
        int res;
#endif
	if (wakeup_with_nul_byte)
	{
	    res = write(wakeup_fd, "\0", 1);
	} else {
	    unsigned char byte = (unsigned char)signum;
	    res = write(wakeup_fd, &byte, 1);
	}

        /* the return value is ignored here */
      }
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

void pypysig_reinstall(int signum)
{
#ifdef SA_RESTART
    /* Assume sigaction was used.  We did not pass SA_RESETHAND to
       sa_flags, so there is nothing to do here. */
#else
# ifdef SIGCHLD
    /* To avoid infinite recursion, this signal remains
       reset until explicitly re-instated.  (Copied from CPython) */
    if (signum != SIGCHLD)
# endif
    pypysig_setflag(signum);
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
            pypysig_occurred = 1;   /* maybe another signal is pending */
            return i;
          }
    }
  return -1;  /* no pending signal */
}

int pypysig_set_wakeup_fd(int fd, int with_nul_byte)
{
  int old_fd = wakeup_fd;
  wakeup_fd = fd;
  wakeup_with_nul_byte = with_nul_byte;
  return old_fd;
}
