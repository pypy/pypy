

/* "compiler fence" for preventing reordering of loads/stores to
   non-volatiles */
#define CFENCE          asm volatile ("":::"memory")


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
bool_cas(volatile unsigned long* ptr, unsigned long old, unsigned long _new)
{
    unsigned long prev;
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
  /* use "memory" here to make sure that gcc will reload the
     relevant data from memory after the spinloop */
  asm volatile ("pause":::"memory");
}
