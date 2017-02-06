#pragma once

#include "vmprof.h"

#define SINGLE_BUF_SIZE (8192 - 2 * sizeof(unsigned int))

#ifdef VMPROF_WINDOWS
#include "msiinttypes/inttypes.h"
#include "msiinttypes/stdint.h"
#else
#include <inttypes.h>
#include <stdint.h>
#endif


RPY_EXTERN char *vmprof_init(int fd, double interval, int memory,
                     int lines, const char *interp_name, int native);
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
