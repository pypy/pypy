#ifndef _RPY_STMGCINTF_H
#define _RPY_STMGCINTF_H


/* meant to be #included after src_stm/stmgc.h */

#include "stmgc.h"
#include "stm/atomic.h"    /* for spin_loop() and write_fence() */

extern __thread struct stm_thread_local_s stm_thread_local;
extern stm_char *pypy_stm_nursery_low_fill_mark;

void pypy_stm_setup(void);
void pypy_stm_setup_prebuilt(void);   /* generated into stm_prebuilt.c */
long pypy_stm_enter_callback_call(void);
void pypy_stm_leave_callback_call(long);

static inline int pypy_stm_should_break_transaction(void)
{
    /* we should break the current transaction if we have used more than
       some initial portion of the nursery, or if we are running inevitable */
    return (STM_SEGMENT->nursery_current >= pypy_stm_nursery_low_fill_mark ||
            STM_SEGMENT->jmpbuf_ptr == NULL);
}


#if 0    /* fprinting versions */
# define spinlock_acquire(lock, targetvalue)                            \
    do { if (__sync_bool_compare_and_swap(&(lock), 0, (targetvalue))) { \
             dprintf(("<<< locked %d\n", (int)targetvalue));            \
             break;                                                     \
         }                                                              \
         do { spin_loop(); } while (lock);                              \
    } while (1)
# define spinlock_release(lock)                                         \
    do { dprintf(("unlocked >>>\n")); write_fence();                    \
         assert((lock) != 0); (lock) = 0; } while (0)
#else
# define spinlock_acquire(lock, targetvalue)                                 \
    do { if (__sync_bool_compare_and_swap(&(lock), 0, (targetvalue))) break; \
         do { spin_loop(); } while (lock);                                   \
    } while (1)
# define spinlock_release(lock)                                 \
    do { write_fence(); assert((lock) != 0); (lock) = 0; } while (0)
#endif


#endif  /* _RPY_STMGCINTF_H */
