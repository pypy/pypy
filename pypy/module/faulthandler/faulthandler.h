#ifndef PYPY_FAULTHANDLER_H
#define PYPY_FAULTHANDLER_H

#include "src/precommondefs.h"

RPY_EXTERN char *pypy_faulthandler_setup(void dump_callback(void));
RPY_EXTERN void pypy_faulthandler_teardown(void);

RPY_EXTERN char *pypy_faulthandler_enable(int fd, int all_threads);
RPY_EXTERN void pypy_faulthandler_disable(void);
RPY_EXTERN int pypy_faulthandler_is_enabled(void);

RPY_EXTERN void pypy_faulthandler_write(char *);
RPY_EXTERN void pypy_faulthandler_write_int(long);

RPY_EXTERN void pypy_faulthandler_dump_traceback(int fd, int all_threads);

/*
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
*/

#endif  /* PYPY_FAULTHANDLER_H */
