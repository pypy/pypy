/*** Extendable Timestamps
 *
 * This is a C version of rstm_r5/stm/et.hpp.
 * See http://www.cs.rochester.edu/research/synchronization/rstm/api.shtml
 *
 */

#ifndef _ET_H
#define _ET_H

#include <setjmp.h>
#include "src/commondefs.h"


void stm_setup_size_getter(long(*)(void*));

void stm_set_tls(void *, long);
void *stm_get_tls(void);
void stm_del_tls(void);

void *stm_tldict_lookup(void *);
void stm_tldict_add(void *, void *);
void stm_tldict_enum(void(*)(void*, void*, void*));

char      stm_read_int1(void *, long);
short     stm_read_int2(void *, long);
int       stm_read_int4(void *, long);
long long stm_read_int8(void *, long);


#ifdef RPY_STM_ASSERT
#  define STM_CCHARP1(arg)    char* arg
#  define STM_EXPLAIN1(info)  info
#else
#  define STM_CCHARP1(arg)    void
#  define STM_EXPLAIN1(info)  /* nothing */
#endif


void* stm_perform_transaction(void*(*)(void*, long), void*);
void stm_try_inevitable(STM_CCHARP1(why));
void stm_abort_and_retry(void);
long stm_debug_get_state(void);  /* -1: descriptor_init() was not called
                                     0: not in a transaction
                                     1: in a regular transaction
                                     2: in an inevitable transaction */
long stm_thread_id(void);  /* returns a unique thread id,
                              or 0 if descriptor_init() was not called */
long stm_in_transaction(void);
void _stm_activate_transaction(long);


/************************************************************/

/* These are the same two flags as defined in stmgc.py */

enum {
  first_gcflag      = 1L << (PYPY_LONG_BIT / 2),
  GCFLAG_GLOBAL     = first_gcflag << 0,
  GCFLAG_WAS_COPIED = first_gcflag << 1
};


#define RPY_STM_ARRAY(T, size, ptr, field)                      \
    _RPY_STM(T, size, ptr, ((char*)&field)-((char*)ptr), field)

#define RPY_STM_FIELD(T, size, STRUCT, ptr, field)              \
    _RPY_STM(T, size, ptr, offsetof(STRUCT, field), ptr->field)

#define _RPY_STM(T, size, ptr, offset, field)           \
    (((*(long*)ptr) & GCFLAG_GLOBAL) == 0 ? field :     \
     (T)stm_read_int##size(ptr, offset))


#endif  /* _ET_H */
