#ifndef PYPY_FAULTHANDLER_H
#define PYPY_FAULTHANDLER_H

#include <signal.h>
#include "src/precommondefs.h"

RPY_EXTERN int pypy_faulthandler_read_null(void);
RPY_EXTERN void pypy_faulthandler_sigsegv(void);
RPY_EXTERN int pypy_faulthandler_sigfpe(void);
RPY_EXTERN void pypy_faulthandler_sigabrt();
#ifdef SIGBUS
RPY_EXTERN void pypy_faulthandler_sigbus(void);
#endif

#ifdef SIGILL
RPY_EXTERN void pypy_faulthandler_sigill(void);
#endif

#endif  /* PYPY_FAULTHANDLER_H */
