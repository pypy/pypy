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


void stm_descriptor_init(void);
void stm_descriptor_done(void);
void* stm_perform_transaction(void*(*)(void*), void*);
void stm_begin_transaction(jmp_buf* buf);
long stm_commit_transaction(void);
long stm_read_word(long* addr);
void stm_write_word(long* addr, long val);
void stm_try_inevitable(void);
void stm_begin_inevitable_transaction(void);
void stm_abort_and_retry(void);

#define STM_begin_transaction()         ; \
       jmp_buf _jmpbuf;                   \
       setjmp(_jmpbuf);                   \
       stm_begin_transaction(&_jmpbuf)

// XXX little-endian only!
#define STM_read_partial_word(T, base, offset)                          \
    (T)(stm_read_word(                                                  \
           (long*)(((char*)(base)) + ((offset) & ~(sizeof(void*)-1))))  \
        >> (8 * ((offset) & (sizeof(void*)-1))))

void stm_write_partial_word(int fieldsize, char *base, long offset,
                            unsigned long nval);

double stm_read_double(long *addr);
void stm_write_double(long *addr, double val);
float stm_read_float(long *addr);
void stm_write_float(long *addr, float val);
#if PYPY_LONG_BIT == 32
long long stm_read_doubleword(long *addr);
void stm_write_doubleword(long *addr, long long val);
#endif


#endif  /* _ET_H */
