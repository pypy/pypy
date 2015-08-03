
RPY_EXTERN char *rpython_vmprof_init(void);
RPY_EXTERN void rpython_vmprof_ignore_signals(int);
RPY_EXTERN int rpython_vmprof_enable(int, long);
RPY_EXTERN int rpython_vmprof_disable(void);
RPY_EXTERN void rpython_vmprof_write_buf(char *, long);
