#ifndef _PYPY_SIGNALS_H
#define _PYPY_SIGNALS_H

/* utilities to set a signal handler */
void pypysig_ignore(int signum);  /* signal will be ignored (SIG_IGN) */
void pypysig_default(int signum); /* signal will do default action (SIG_DFL) */
void pypysig_setflag(int signum); /* signal will set a flag which can be
                                     queried with pypysig_poll() */
void pypysig_reinstall(int signum);
int pypysig_set_wakeup_fd(int fd);

/* utility to poll for signals that arrived */
int pypysig_poll(void);   /* => signum or -1 */

/* When a signal is received, pypysig_counter is set to -1. */
/* This is a struct for the JIT. See rsignal.py. */
struct pypysig_long_struct {
    long value;
};
extern struct pypysig_long_struct pypysig_counter;

/* some C tricks to get/set the variable as efficiently as possible:
   use macros when compiling as a stand-alone program, but still
   export a function with the correct name for testing */
void *pypysig_getaddr_occurred(void);
#define pypysig_getaddr_occurred()   ((void *)(&pypysig_counter))

#endif
