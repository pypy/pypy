/*** Extendable Timestamps
 *
 * This is a C version of rstm_r5/stm/et.hpp.
 * See http://www.cs.rochester.edu/research/synchronization/rstm/api.shtml
 *
 */

#ifndef _ET_H
#define _ET_H

#include <setjmp.h>


void stm_descriptor_init(void);
void stm_descriptor_done(void);
void* stm_perform_transaction(void*(*)(void*), void*);
void stm_begin_transaction(jmp_buf* buf);
long stm_commit_transaction(void);
void* stm_read_word(void** addr);
void stm_write_word(void** addr, void* val);
void stm_try_inevitable(void);
void stm_begin_inevitable_transaction(void);
void stm_abort_and_retry(void);

#define stm_begin_transaction_inline()  ; \
       jmp_buf _jmpbuf;                   \
       setjmp(_jmpbuf);                   \
       stm_begin_transaction(&_jmpbuf)


#endif  /* _ET_H */
