/*** Extendable Timestamps
 *
 * Documentation:
 * https://bitbucket.org/pypy/extradoc/raw/extradoc/talk/stm2012/stmimpl.rst
 *
 * This is very indirectly based on rstm_r5/stm/et.hpp.
 * See http://www.cs.rochester.edu/research/synchronization/rstm/api.shtml
 *
 * Stand-alone version of these files, including random stress-tests:
 * https://bitbucket.org/arigo/arigo/raw/default/hack/stm/c2
 *
 */

#ifndef _ET_H
#define _ET_H

#include <stddef.h>
#include <setjmp.h>


/* These are partly the same flags as defined in stmgc.py, as well as
   nogcstm.py.  Keep in sync! */
enum {
  _first_gcflag            = 1L << (PYPY_LONG_BIT / 2),
  GCFLAG_GLOBAL            = _first_gcflag << 0,
  GCFLAG_POSSIBLY_OUTDATED = _first_gcflag << 1,
  GCFLAG_NOT_WRITTEN       = _first_gcflag << 2,
  GCFLAG_LOCAL_COPY        = _first_gcflag << 3,
  GCFLAG_VISITED           = _first_gcflag << 4,

  GCFLAG_PREBUILT          = GCFLAG_GLOBAL|GCFLAG_NOT_WRITTEN,
  REV_INITIAL              = 1,
};

typedef struct pypy_header0 *gcptr;
/*declared in structdef.h as {
    Signed h_tid;
    void *h_revision;
}*/

#define STM_BARRIER_P2R(P)                                              \
    (__builtin_expect((((gcptr)(P))->h_tid & GCFLAG_GLOBAL) == 0, 1) ?  \
     (P) : (typeof(P))stm_DirectReadBarrier(P))

#define STM_BARRIER_G2R(G)                                          \
    (assert(((gcptr)(G))->h_tid & GCFLAG_GLOBAL),                   \
     (typeof(G))stm_DirectReadBarrier(G))

#define STM_BARRIER_O2R(O)                                              \
    (__builtin_expect((((gcptr)(O))->h_tid & GCFLAG_POSSIBLY_OUTDATED) == 0, \
                      1) ?                                              \
     (O) : (typeof(O))stm_RepeatReadBarrier(O))

/*#define STM_READ_BARRIER_P_FROM_R(P, R_container, offset)             \
    (__builtin_expect((((gcptr)(P))->h_tid & GCFLAG_GLOBAL) == 0, 1) ?  \
     (P) : (typeof(P))stm_DirectReadBarrierFromR((P),            \
                                              (R_container),     \
                                              offset))*/

#define STM_BARRIER_P2W(P)                                                  \
    (__builtin_expect((((gcptr)(P))->h_tid & GCFLAG_NOT_WRITTEN) == 0, 1) ? \
     (P) : (typeof(P))stm_WriteBarrier(P))

#define STM_BARRIER_G2W(G)                              \
    (assert(((gcptr)(G))->h_tid & GCFLAG_GLOBAL),       \
     (typeof(G))stm_WriteBarrier(G))

#define STM_BARRIER_R2W(R)                                                  \
    (__builtin_expect((((gcptr)(R))->h_tid & GCFLAG_NOT_WRITTEN) == 0, 1) ? \
     (R) : (typeof(R))stm_WriteBarrierFromReady(R))

#define STM_BARRIER_O2W(R)  STM_BARRIER_R2W(R)   /* same logic works here */

#define STM_PTR_EQ(P1, P2)                      \
    stm_PtrEq((gcptr)(P1), (gcptr)(P2))

#define OP_STM_THREADLOCALREF_LLSET(P, X, IGNORED)          \
    stm_ThreadLocalRef_LLSet((void **)(P), (void *)(X))

/* special usage only */
#define OP_STM_READ_BARRIER(P, R)   R = STM_BARRIER_P2R(P)
#define OP_STM_WRITE_BARRIER(P, W)   W = STM_BARRIER_P2W(P)


void BeginTransaction(jmp_buf *);
void BeginInevitableTransaction(void);
//int _FakeReach(gcptr);
void CommitTransaction(void);
void BecomeInevitable(const char *why);
//void BeginInevitableTransaction(void);
int DescriptorInit(void);
void DescriptorDone(void);

//gcptr Allocate(size_t size, int gctid);
_Bool stm_PtrEq(gcptr P1, gcptr P2);

void *stm_DirectReadBarrier(void *);
void *stm_DirectReadBarrierFromR(void *, void *, size_t);
void *stm_RepeatReadBarrier(void *);
void *stm_WriteBarrier(void *);
void *stm_WriteBarrierFromReady(void *);
//gcptr _NonTransactionalReadBarrier(gcptr);

void stm_ThreadLocalRef_LLSet(void **P, void *X);


extern void *pypy_g__stm_duplicate(void *);
extern void pypy_g__stm_enum_callback(void *, void *);
void stm_set_tls(void *newtls);
void *stm_get_tls(void);
void stm_del_tls(void);
gcptr stm_tldict_lookup(gcptr);     /* for tests only */
void stm_tldict_add(gcptr, gcptr);  /* for tests only */
void stm_tldict_enum(void);
long stm_in_transaction(void);
long stm_is_inevitable(void);
void stm_add_atomic(long delta);
long stm_get_atomic(void);
long stm_should_break_transaction(void);
void stm_set_transaction_length(long length_max);
void stm_perform_transaction(long(*callback)(void*, long), void *arg,
                             void *save_and_restore);
void stm_abort_and_retry(void);
void stm_abort_info_push(void *, void *);
void stm_abort_info_pop(long);
char *stm_inspect_abort_info(void);
long stm_extraref_llcount(void);
gcptr *stm_extraref_lladdr(long);

#ifdef USING_NO_GC_AT_ALL
# define OP_GC_ADR_OF_ROOT_STACK_TOP(r)   r = NULL
void stm_nogc_start_transaction(void);
void stm_nogc_stop_transaction(void);
gcptr stm_nogc_allocate(size_t);
# undef OP_BOEHM_ZERO_MALLOC
# define OP_BOEHM_ZERO_MALLOC(size, r, restype, is_atomic, is_varsize)  \
    r = (restype) stm_nogc_allocate(size)
#endif

#endif  /* _ET_H */
