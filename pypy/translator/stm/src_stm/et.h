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

#include <setjmp.h>


/* These are partly the same flags as defined in stmgc.py.  Keep in sync! */
enum {
  _first_gcflag            = 1L << (PYPY_LONG_BIT / 2),
  GCFLAG_GLOBAL            = _first_gcflag << 0,
  GCFLAG_POSSIBLY_OUTDATED = _first_gcflag << 1,
  GCFLAG_NOT_WRITTEN       = _first_gcflag << 2,

  GCFLAG_PREBUILT          = GCFLAG_GLOBAL|GCFLAG_NOT_WRITTEN,
  REV_INITIAL              = 1
};

typedef struct pypy_header0 *gcptr;
/*declared in structdef.h as {
    Signed h_tid;
    void *h_revision;
}*/

#define STM_BARRIER_P2R(P)                                              \
    (__builtin_expect((((gcptr)(P))->h_tid & GCFLAG_GLOBAL) == 0, 1) ?  \
     (P) : (typeof(P))_DirectReadBarrier((gcptr)(P)))

#define STM_BARRIER_G2R(G)                                          \
    (assert(((gcptr)(G))->h_tid & GCFLAG_GLOBAL),                   \
     (typeof(G))_DirectReadBarrier((gcptr)(G)))

/*#define STM_READ_BARRIER_P_FROM_R(P, R_container, offset)             \
    (__builtin_expect((((gcptr)(P))->h_tid & GCFLAG_GLOBAL) == 0, 1) ?  \
     (P) : (typeof(P))_DirectReadBarrierFromR((gcptr)(P),               \
                                              (gcptr)(R_container),     \
                                              offset))*/

#define STM_BARRIER_P2W(P)                                                  \
    (__builtin_expect((((gcptr)(P))->h_tid & GCFLAG_NOT_WRITTEN) == 0, 1) ? \
     (P) : (typeof(P))_WriteBarrier((gcptr)(P)))

#define STM_BARRIER_R2W(R)                                                  \
    (__builtin_expect((((gcptr)(R))->h_tid & GCFLAG_NOT_WRITTEN) == 0, 1) ? \
     (R) : (typeof(R))_WriteBarrierFromReady((gcptr)(R)))

/* declared in structdef.h:
struct gcroot_s {
    gcptr R, L;
    Signed v;
};*/

void BeginTransaction(jmp_buf *);
struct gcroot_s *FindRootsForLocalCollect(void);
int _FakeReach(gcptr);
void CommitTransaction(void);
void BecomeInevitable(void);
//void BeginInevitableTransaction(void);
void DescriptorInit(void);
void DescriptorDone(void);

//gcptr Allocate(size_t size, int gctid);
_Bool PtrEq(gcptr P1, gcptr P2);

gcptr _DirectReadBarrier(gcptr);
gcptr _DirectReadBarrierFromR(gcptr, gcptr, size_t);
gcptr _WriteBarrier(gcptr);
gcptr _WriteBarrierFromReady(gcptr);
//gcptr _NonTransactionalReadBarrier(gcptr);


extern size_t pypy_g__stm_getsize(gcptr);


#endif  /* _ET_H */
