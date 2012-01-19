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

#ifdef RPY_STM_ASSERT
#  define STM_CCHARP(arg)     , char* arg
#  define STM_CCHARP1(arg)    char* arg
#  define STM_EXPLAIN(info)   , info
#  define STM_EXPLAIN1(info)  info
#else
#  define STM_CCHARP(arg)     /* nothing */
#  define STM_CCHARP1(arg)    void
#  define STM_EXPLAIN(info)   /* nothing */
#  define STM_EXPLAIN1(info)  /* nothing */
#endif


void stm_descriptor_init(void);
void stm_descriptor_done(void);
void* stm_perform_transaction(void*(*)(void*), void*);
void stm_begin_transaction(jmp_buf* buf);
long stm_commit_transaction(void);
long stm_read_word(long* addr);
void stm_write_word(long* addr, long val);
void stm_try_inevitable(STM_CCHARP1(why));
void stm_try_inevitable_if(jmp_buf* buf  STM_CCHARP(why));
void stm_begin_inevitable_transaction(void);
void stm_abort_and_retry(void);
void stm_descriptor_init_and_being_inevitable_transaction(void);
void stm_commit_transaction_and_descriptor_done(void);
long stm_debug_get_state(void);  /* -1: descriptor_init() was not called
                                     0: not in a transaction
                                     1: in a regular transaction
                                     2: in an inevitable transaction */

/* for testing only: */
#define STM_begin_transaction()         ; \
       jmp_buf _jmpbuf;                   \
       setjmp(_jmpbuf);                   \
       stm_begin_transaction(&_jmpbuf)

#define STM_DECLARE_VARIABLE()          ; jmp_buf jmpbuf
#define STM_MAKE_INEVITABLE()           stm_try_inevitable_if(&jmpbuf  \
                                                        STM_EXPLAIN("return"))

// XXX little-endian only!
#define STM_read_partial_word(T, base, offset)                          \
    (T)(stm_read_word(                                                  \
           (long*)(((char*)(base)) + ((offset) & ~(sizeof(void*)-1))))  \
        >> (8 * ((offset) & (sizeof(void*)-1))))

unsigned long stm_read_partial_word(int fieldsize, void *addr);
void stm_write_partial_word(int fieldsize, void *addr, unsigned long nval);

double stm_read_double(long *addr);
void stm_write_double(long *addr, double val);
float stm_read_float(long *addr);
void stm_write_float(long *addr, float val);
#if PYPY_LONG_BIT == 32
long long stm_read_doubleword(long *addr);
void stm_write_doubleword(long *addr, long long val);
#endif


#endif  /* _ET_H */
