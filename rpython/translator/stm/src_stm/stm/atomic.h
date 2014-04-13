/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _STM_ATOMIC_H
#define _STM_ATOMIC_H

/* spin_loop() corresponds to the PAUSE instruction on x86.  On
   other architectures, we generate no instruction (but still need
   the compiler barrier); if on another architecture you find the
   corresponding instruction, feel free to add it here.
*/

/* write_fence() is a function that inserts a "write fence".  The
   goal is to make sure that past writes are really pushed to memory
   before the future writes.  We assume that the corresponding "read
   fence" effect is done automatically by a corresponding
   __sync_bool_compare_and_swap().

   On x86, this is done automatically by the CPU; we only need a
   compiler barrier (asm("memory")).

   On other architectures, we use __sync_synchronize() as a general
   fall-back, but we might have more efficient alternative on some other
   platforms too.
*/


#if defined(__i386__) || defined(__amd64__)

# define HAVE_FULL_EXCHANGE_INSN
  static inline void spin_loop(void) { asm("pause" : : : "memory"); }
  static inline void write_fence(void) { asm("" : : : "memory"); }

#else

  static inline void spin_loop(void) { asm("" : : : "memory"); }
  static inline void write_fence(void) { __sync_synchronize(); }

#endif


#define spinlock_acquire(lock)                                          \
    do { if (LIKELY(__sync_lock_test_and_set(&(lock), 1) == 0)) break;  \
         spin_loop(); } while (1)
#define spinlock_release(lock)                                          \
    do { assert((lock) == 1);                                           \
         __sync_lock_release(&(lock)); } while (0)


#endif  /* _STM_ATOMIC_H */
