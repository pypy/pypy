
RPY_EXTERN char *vmprof_init(int, double, char *);
RPY_EXTERN void vmprof_ignore_signals(int);
RPY_EXTERN int vmprof_enable(void);
RPY_EXTERN int vmprof_disable(void);
RPY_EXTERN int vmprof_register_virtual_function(char *, long, int);
RPY_EXTERN void* vmprof_stack_new(void);
RPY_EXTERN int vmprof_stack_append(void*, long);
RPY_EXTERN long vmprof_stack_pop(void*);
RPY_EXTERN void vmprof_stack_free(void*);

RPY_EXTERN char * jitlog_init(int);
RPY_EXTERN void jitlog_try_init_using_env(void);
RPY_EXTERN int jitlog_enabled();
RPY_EXTERN void jitlog_write_marked(int, char*, int);
RPY_EXTERN void jitlog_teardown();
