#include <stdint.h>

RPY_EXTERN char *vmprof_init(int, double, char *);
RPY_EXTERN void vmprof_ignore_signals(int);
RPY_EXTERN int vmprof_enable(void);
RPY_EXTERN int vmprof_disable(void);
RPY_EXTERN int vmprof_register_virtual_function(char *, long, int);
RPY_EXTERN void* vmprof_stack_new(void);
RPY_EXTERN int vmprof_stack_append(void*, long);
RPY_EXTERN long vmprof_stack_pop(void*);
RPY_EXTERN void vmprof_stack_free(void*);
RPY_EXTERN intptr_t vmprof_get_traceback(void *, void *, intptr_t*, intptr_t);

#define RVMPROF_TRACEBACK_ESTIMATE_N(num_entries)  (2 * (num_entries) + 4)
