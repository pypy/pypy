#ifndef PYPY_FAULTHANDLER_H
#define PYPY_FAULTHANDLER_H

#include <signal.h>
#include "src/precommondefs.h"

RPY_EXPORTED_FOR_TESTS int pypy_faulthandler_read_null(void);
RPY_EXPORTED_FOR_TESTS void pypy_faulthandler_sigsegv(void);
RPY_EXPORTED_FOR_TESTS int pypy_faulthandler_sigfpe(void);
RPY_EXPORTED_FOR_TESTS void pypy_faulthandler_sigabrt();
#ifdef SIGBUS
RPY_EXPORTED_FOR_TESTS void pypy_faulthandler_sigbus(void);
#endif

#ifdef SIGILL
RPY_EXPORTED_FOR_TESTS void pypy_faulthandler_sigill(void);
#endif

#endif  /* PYPY_FAULTHANDLER_H */
