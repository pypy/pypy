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
void stm_tlidct_enum(void(*)(void*, void*));

long stm_read_word(void *, long);


#if 0

#ifdef RPY_STM_ASSERT
#  define STM_CCHARP1(arg)    char* arg
#  define STM_EXPLAIN1(info)  info
#else
#  define STM_CCHARP1(arg)    void
#  define STM_EXPLAIN1(info)  /* nothing */
#endif


void* stm_perform_transaction(void*(*)(void*, long), void*);
long stm_read_word(long* addr);
void stm_write_word(long* addr, long val);
void stm_try_inevitable(STM_CCHARP1(why));
void stm_abort_and_retry(void);
long stm_debug_get_state(void);  /* -1: descriptor_init() was not called
                                     0: not in a transaction
                                     1: in a regular transaction
                                     2: in an inevitable transaction */
long stm_thread_id(void);  /* returns a unique thread id,
                              or 0 if descriptor_init() was not called */

// XXX little-endian only!
/* this macro is used if 'base' is a word-aligned pointer and 'offset'
   is a compile-time constant */
#define stm_fx_read_partial(base, offset)                               \
       (stm_read_word(                                                  \
           (long*)(((char*)(base)) + ((offset) & ~(sizeof(void*)-1))))  \
        >> (8 * ((offset) & (sizeof(void*)-1))))

unsigned char stm_read_partial_1(void *addr);
unsigned short stm_read_partial_2(void *addr);
void stm_write_partial_1(void *addr, unsigned char nval);
void stm_write_partial_2(void *addr, unsigned short nval);
#if PYPY_LONG_BIT == 64
unsigned int stm_read_partial_4(void *addr);
void stm_write_partial_4(void *addr, unsigned int nval);
#endif

double stm_read_double(long *addr);
void stm_write_double(long *addr, double val);
float stm_read_float(long *addr);
void stm_write_float(long *addr, float val);
#if PYPY_LONG_BIT == 32
long long stm_read_doubleword(long *addr);
void stm_write_doubleword(long *addr, long long val);
#endif

#endif  /* 0 */


#endif  /* _ET_H */
