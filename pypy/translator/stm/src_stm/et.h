/*** Extendable Timestamps
 *
 * This is a (heavily modified) C version of rstm_r5/stm/et.hpp.
 * See http://www.cs.rochester.edu/research/synchronization/rstm/api.shtml
 *
 */

#ifndef _ET_H
#define _ET_H

#include <setjmp.h>


/* see comments in ../stmgcintf.py */
void stm_set_tls(void *);
void *stm_get_tls(void);
void stm_del_tls(void);
long stm_thread_id(void);

void *stm_tldict_lookup(void *);
void stm_tldict_add(void *, void *);
void stm_tldict_enum(void);

long stm_descriptor_init(void);
void stm_descriptor_done(void);

void stm_begin_inevitable_transaction(void);
void stm_commit_transaction(void);

long stm_in_transaction(void);
long stm_is_inevitable(void);

void stm_perform_transaction(long(*)(void*, long), void*, void*);

/* these functions are declared by generated C code from pypy.rlib.rstm
   and from the GC (see llop.nop(...)) */
extern void pypy_g__stm_thread_starting(void);
extern void pypy_g__stm_thread_stopping(void);
extern void *pypy_g__stm_run_transaction(void *, long);
extern long pypy_g__stm_getsize(void *);
extern void pypy_g__stm_enum_callback(void *, void *, void *);

char      stm_read_int1(void *, long);
short     stm_read_int2(void *, long);
int       stm_read_int4(void *, long);
long long stm_read_int8(void *, long);
double    stm_read_int8f(void *, long);
float     stm_read_int4f(void *, long);


#if 1  /* #ifdef RPY_STM_ASSERT --- but it's always useful to have this info */
#  define STM_CCHARP1(arg)    char* arg
#  define STM_EXPLAIN1(info)  info
#else
#  define STM_CCHARP1(arg)    void
#  define STM_EXPLAIN1(info)  /* nothing */
#endif


void stm_try_inevitable(STM_CCHARP1(why));
void stm_abort_and_retry(void);

void stm_copy_transactional_to_raw(void *src, void *dst, long size);


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
