/* Imported by rpython/translator/stm/import_stmgc.py */
#ifndef _SRCSTM_ATOMIC_OPS_
#define _SRCSTM_ATOMIC_OPS_

#include <assert.h>
#define IMPLIES(a, b)   (!(a) || (b))

/* Ask the compiler to really reload the revision_t argument from memory.
   That's all that this macro does; it does not imply any type of barrier.
   Consider it as meaning: I want to read (or possibly write) a shared
   value out of explicit synchronization now. */
#define ACCESS_ONCE(x) (*(volatile revision_t *)&(x))

#define UNLIKELY(test)  __builtin_expect(test, 0)


#if defined(__amd64__) || defined(__i386__)
#  define smp_wmb()       asm volatile ("":::"memory")
#  define smp_spinloop()  asm volatile ("pause":::"memory")
#elif defined(__powerpc__)
#  define smp_wmb()       asm volatile ("lwsync":::"memory")
#  define smp_spinloop()  asm volatile ("":::"memory")   /* fill me? */
#else
#  error "Define smp_wmb() for your architecture"
#endif


#ifdef __llvm__
#  define HAS_SYNC_BOOL_COMPARE_AND_SWAP
#  define HAS_SYNC_FETCH_AND_ADD
#endif

#ifdef __GNUC__
#  if __GNUC__ > 4 || (__GNUC__ == 4 && __GNUC_MINOR__ >= 1)
#    define HAS_SYNC_BOOL_COMPARE_AND_SWAP
#    define HAS_SYNC_FETCH_AND_ADD
#  endif
#endif


#ifdef HAS_SYNC_BOOL_COMPARE_AND_SWAP
#  define bool_cas __sync_bool_compare_and_swap
#else
/* x86 (32 bits and 64 bits) */
static inline _Bool
bool_cas(revision_t *ptr, revision_t old, revision_t _new)
{
    revision_t prev;
#if defined(__amd64__)
    assert(sizeof(revision_t) == 8);
#elif defined(__i386__)
    assert(sizeof(revision_t) == 4);
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

#ifdef HAS_SYNC_FETCH_AND_ADD
#  define fetch_and_add __sync_fetch_and_add
#else
/* x86 (32 bits and 64 bits) */
static inline revision_t
fetch_and_add(revision_t *ptr, revision_t value)
{
    revision_t prev;
#if defined(__amd64__)
    assert(sizeof(revision_t) == 8);
#elif defined(__i386__)
    assert(sizeof(revision_t) == 4);
#else
#   error "the custom version of fetch_and_add() is only for x86 or x86-64"
#endif
    asm volatile("lock;"
#if defined(__amd64__)
                 "xaddq %1, %2;"
#else
                 "xaddl %1, %2;"
#endif
                 : "=r"(prev)
                 : "0"(value), "m"(*ptr)
                 : "memory");
    return prev;
}
/* end */
#endif


#if 0    /* fprinting versions */
# define spinlock_acquire(lock, targetvalue)                            \
    do { if (bool_cas(&(lock), 0, (targetvalue))) {                     \
             dprintf(("<<< locked %d\n", (int)targetvalue));            \
             break;                                                     \
         }                                                              \
         do { smp_spinloop(); } while (ACCESS_ONCE(lock));              \
    } while (1)
# define spinlock_release(lock)                                         \
    do { dprintf(("unlocked >>>\n")); smp_wmb();                        \
         assert((lock) != 0); (lock) = 0; } while (0)
#else
# define spinlock_acquire(lock, targetvalue)                    \
    do { if (bool_cas(&(lock), 0, (targetvalue))) break;        \
         do { smp_spinloop(); } while (ACCESS_ONCE(lock));      \
    } while (1)
# define spinlock_release(lock)                                 \
    do { smp_wmb(); assert((lock) != 0); (lock) = 0; } while (0)
#endif


#endif  /* _SRCSTM_ATOMIC_OPS_ */
