#ifndef _RPY_STMGCINTF_H
#define _RPY_STMGCINTF_H


/* meant to be #included after src_stm/stmgc.h */

#include "stmgc.h"
#include "stm/atomic.h"    /* for spin_loop() and write_fence() */

extern __thread struct stm_thread_local_s stm_thread_local;


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
