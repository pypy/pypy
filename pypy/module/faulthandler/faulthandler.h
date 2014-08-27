#ifndef PYPY_FAULTHANDLER_H
#define PYPY_FAULTHANDLER_H

#include <signal.h>

int pypy_faulthandler_read_null(void);
void pypy_faulthandler_sigsegv(void);
int pypy_faulthandler_sigfpe(void);
void pypy_faulthandler_sigabrt();
#ifdef SIGBUS
void pypy_faulthandler_sigbus(void);
#endif

#ifdef SIGILL
void pypy_faulthandler_sigill(void);
#endif

#endif  /* PYPY_FAULTHANDLER_H */
