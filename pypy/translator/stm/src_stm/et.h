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
#include <stdint.h>
#include <setjmp.h>


#define GCFLAG_GLOBAL              0x10000
#define GCFLAG_POSSIBLY_OUTDATED   0x20000
#define GCFLAG_NOT_WRITTEN         0x40000

#define GCFLAG_PREBUILT            (GCFLAG_GLOBAL|GCFLAG_NOT_WRITTEN)
#define REV_INITIAL                1

typedef uintptr_t revision_t;

typedef struct pypy_header0 {
    long h_tid;
    revision_t h_revision;
} *gcptr;


#define STM_READ_BARRIER_P(P)                                           \
    (__builtin_expect((((gcptr)(P))->h_tid & GCFLAG_GLOBAL) == 0, 1) ?  \
     (P) : (typeof(P))_DirectReadBarrier((gcptr)(P)))

#define STM_READ_BARRIER_P_FROM_R(P, R_container, offset)               \
    (__builtin_expect((((gcptr)(P))->h_tid & GCFLAG_GLOBAL) == 0, 1) ?  \
     (P) : (typeof(P))_DirectReadBarrierFromR((gcptr)(P),               \
                                              (gcptr)(R_container),     \
                                              offset))

#define STM_WRITE_BARRIER_P(R)                                          \
    (__builtin_expect((((gcptr)(R))->h_tid & GCFLAG_NOT_WRITTEN) == 0, 1) ? \
     (R) : (typeof(R))_WriteBarrier((gcptr)(R)))

#define STM_WRITE_BARRIER_R(R)                                          \
    (__builtin_expect((((gcptr)(R))->h_tid & GCFLAG_NOT_WRITTEN) == 0, 1) ? \
     (R) : (typeof(R))_WriteBarrierFromReady((gcptr)(R)))

#define STM_NONTRANSACTIONAL_READ_BARRIER(P)                            \
    ((typeof(P))_NonTransactionalReadBarrier((gcptr)(P)))

#define _REACH(P) _FakeReach((gcptr)(P))

#define BEGIN_TRANSACTION                         \
  {                                               \
    jmp_buf _jmpbuf;                              \
    setjmp(_jmpbuf);                              \
    BeginTransaction(&_jmpbuf);                   \
    {

#define END_TRANSACTION                           \
    }                                             \
    CommitTransaction();                          \
  }
#define _END_TRANSACTION_NUM(t)                   \
    }                                             \
    t = CommitTransaction();                      \
  }

struct gcroot_s {
    gcptr R, L;
    revision_t v;
};

void BeginTransaction(jmp_buf *);
struct gcroot_s *FindRootsForLocalCollect(void);
int _FakeReach(gcptr);
revision_t CommitTransaction(void);
void BecomeInevitable(void);
//void BeginInevitableTransaction(void);
revision_t DescriptorInit(void);
void DescriptorDone(void);

gcptr Allocate(size_t size, int gctid);
_Bool PtrEq(gcptr P1, gcptr P2);

gcptr _DirectReadBarrier(gcptr);
gcptr _DirectReadBarrierFromR(gcptr, gcptr, size_t);
gcptr _WriteBarrier(gcptr);
gcptr _WriteBarrierFromReady(gcptr);
gcptr _NonTransactionalReadBarrier(gcptr);


extern size_t pypy_g__stm_getsize(gcptr);


#endif  /* _ET_H */
