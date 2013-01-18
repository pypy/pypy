#ifndef _SRCSTM_ATOMIC_OPS_
#define _SRCSTM_ATOMIC_OPS_


/* "compiler fence" for preventing reordering of loads/stores to
   non-volatiles */
#define CFENCE          asm volatile ("":::"memory")

#if defined(__amd64__) || defined(__i386__)
#  define smp_wmb()       CFENCE
#  define smp_spinloop()  asm volatile ("pause")
#elif defined(__powerpc__)
#  define smp_wmb()       asm volatile ("lwsync":::"memory")
#  define smp_spinloop()  /* fill me? */
#else
#  error "Define smp_wmb() for your architecture"
#endif


#ifdef __llvm__
#  define HAS_SYNC_BOOL_COMPARE_AND_SWAP
#endif

#ifdef __GNUC__
#  if __GNUC__ > 4 || (__GNUC__ == 4 && __GNUC_MINOR__ >= 1)
#    define HAS_SYNC_BOOL_COMPARE_AND_SWAP
#  endif
#endif


#ifdef HAS_SYNC_BOOL_COMPARE_AND_SWAP
#  define bool_cas __sync_bool_compare_and_swap
#else
/* x86 (32 bits and 64 bits) */
static inline _Bool
bool_cas(volatile Unsigned *ptr, Unsigned old, Unsigned _new)
{
    Unsigned prev;
#if defined(__amd64__)
    assert(sizeof(Unsigned) == 8);
#elif defined(__i386__)
    assert(sizeof(Unsigned) == 4);
#else
#   error "the custom version of bool_cas() is only for x86 or x86-64"
#endif
    asm volatile("lock;"
#if defined(__amd64__)
                 "cmpxchgq %1, %2;"
#else
                 "cmpxchgl %1, %2;"
#endif
                 : "=a"(prev)
                 : "q"(_new), "m"(*ptr), "a"(old)
                 : "memory");
    return prev == old;
}
/* end */
#endif


static inline void spinloop(void)
{
  smp_spinloop();
  /* use "memory" here to make sure that gcc will reload the
     relevant data from memory after the spinloop */
  CFENCE;
}


#define stm_lock_acquire(lock)                                          \
     do { while (!bool_cas(&(lock), 0, 1)) spinloop(); } while (0)

#define stm_lock_release(lock)                  \
     (lock) = 0;


#endif  /* _SRCSTM_ATOMIC_OPS_ */
