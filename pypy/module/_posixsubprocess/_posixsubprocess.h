#include <unistd.h>    /* for ssize_t */
#include "src/precommondefs.h"

RPY_EXTERN void
pypy_subprocess_child_exec(
           char *const exec_array[],
           char *const argv[],
           char *const envp[],
           const char *cwd,
           int p2cread, int p2cwrite,
           int c2pread, int c2pwrite,
           int errread, int errwrite,
           int errpipe_read, int errpipe_write,
           int close_fds, int restore_signals,
           int call_setsid,
           long *py_fds_to_keep,
	   ssize_t num_fds_to_keep,
           int (*preexec_fn)(void*),
           void *preexec_fn_arg);

RPY_EXTERN int
pypy_subprocess_cloexec_pipe(int *fds);

RPY_EXTERN void
pypy_subprocess_init(void);
