#ifndef _PYPY_SIGNALS_H
#define _PYPY_SIGNALS_H

#include "src/precommondefs.h"

#include <limits.h>
#ifndef PATH_MAX
#define PATH_MAX 4096
#endif

/* utilities to set a signal handler */
RPY_EXTERN
void pypysig_ignore(int signum);  /* signal will be ignored (SIG_IGN) */
RPY_EXTERN
void pypysig_default(int signum); /* signal will do default action (SIG_DFL) */
RPY_EXTERN
void pypysig_setflag(int signum); /* signal will set a flag which can be
                                     queried with pypysig_poll() */
RPY_EXTERN
void pypysig_reinstall(int signum);
RPY_EXTERN
int pypysig_set_wakeup_fd(int fd, int with_nul_byte);

/* utility to poll for signals that arrived */
RPY_EXTERN
int pypysig_poll(void);   /* => signum or -1 */
RPY_EXTERN
void pypysig_pushback(int signum);

/* When a signal is received, pypysig_counter is set to -1. */
struct pypysig_long_struct_inner {
    Signed value;
};

struct pypysig_long_struct {
    struct pypysig_long_struct_inner inner;
    /* mechanism to start a debugger remotely, via process_vm_writev:
     * - write a .py path to debugger_script_path
     * - set debugger_pending_call to 1
     * - set value to -1
     * */
    char cookie[8];
    Signed debugger_pending_call;
    char debugger_script_path[PATH_MAX];
};
RPY_EXPORTED struct pypysig_long_struct pypysig_counter;

/* some C tricks to get/set the variable as efficiently as possible:
   use macros when compiling as a stand-alone program, but still
   export a function with the correct name for testing */
RPY_EXTERN
void *pypysig_getaddr_occurred(void);
#define pypysig_getaddr_occurred()   ((void *)(&pypysig_counter))

inline static char pypysig_check_and_reset(void) {
    /* used by reverse_debugging */
    char result = --pypysig_counter.inner.value < 0;
    if (result)
        pypysig_counter.inner.value = 100;
    return result;
}

#endif
