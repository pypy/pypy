#ifndef _RPY_STMGCINTF_H
#define _RPY_STMGCINTF_H


#include <errno.h>
#include "stmgc.h"

extern __thread struct stm_thread_local_s stm_thread_local;

void pypy_stm_setup(void);
void pypy_stm_teardown(void);
void pypy_stm_setup_prebuilt(void);        /* generated into stm_prebuilt.c */
void pypy_stm_setup_prebuilt_hashtables(void);  /*  "     "      "          */
void pypy_stm_register_thread_local(void); /* generated into stm_prebuilt.c */
void pypy_stm_unregister_thread_local(void); /* generated into stm_prebuilt.c */

void pypy_stm_memclearinit(object_t *obj, size_t offset, size_t size);

char *_pypy_stm_test_expand_marker(void);
void pypy_stm_setup_expand_marker(long co_filename_ofs,
                                  long co_name_ofs,
                                  long co_firstlineno_ofs,
                                  long co_lnotab_ofs);

long _pypy_stm_count(void);

long pypy_stm_enter_callback_call(void *);
void pypy_stm_leave_callback_call(void *, long);
void pypy_stm_set_transaction_length(double);
void pypy_stm_transaction_break(void);

static void pypy__rewind_jmp_copy_stack_slice(void)
{
    _rewind_jmp_copy_stack_slice(&stm_thread_local.rjthread);
}


#endif  /* _RPY_STMGCINTF_H */
