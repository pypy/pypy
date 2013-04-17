/* -*- c-basic-offset: 2 -*- */

/* XXX assumes that time never wraps around (in a 'long'), which may be
 * correct on 64-bit machines but not on 32-bit machines if the process
 * runs for long enough.
 */

#ifndef _GNU_SOURCE
# define _GNU_SOURCE
#endif
#ifndef _XOPEN_SOURCE
# define _XOPEN_SOURCE 500
#endif

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <pthread.h>
#include <time.h>

#ifndef RPY_STM
/* for tests, a few custom defines */
#define RPY_STM_DEBUG_PRINT     1
#define PYPY_DEBUG_START(s)     fprintf(stderr, "start: %s\n", s)
#define PYPY_DEBUG_STOP(s)      fprintf(stderr, " stop: %s\n", s)
#define PYPY_HAVE_DEBUG_PRINTS  1
#define PYPY_DEBUG_FILE         stderr
#else
#define RPY_STM_DEBUG_PRINT     1    /* for now */
#endif

#include "et.h"

/************************************************************/

typedef Unsigned revision_t;
#define LOCKED  ((revision_t)-0x10000)

#include "atomic_ops.h"
#include "lists.c"

/************************************************************/

#define ABORT_REASONS 5
#define SPINLOOP_REASONS 4

struct tx_descriptor {
  jmp_buf *setjmp_buf;
  revision_t start_time;
  revision_t my_lock;
  long atomic;   /* 0 = not atomic, > 0 atomic */
  unsigned long count_reads;
  unsigned long reads_size_limit;        /* see should_break_tr. */
  unsigned long reads_size_limit_nonatomic;
  int active;    /* 0 = inactive, 1 = regular, 2 = inevitable */
  int readonly_updates;
  struct timespec start_real_time;
  unsigned int num_commits;
  unsigned int num_aborts[ABORT_REASONS];
  unsigned int num_spinloops[SPINLOOP_REASONS];
  struct GcPtrList list_of_read_objects;
  struct GcPtrList gcroots;
  struct G2L global_to_local;
  struct GcPtrList undolog;
  struct GcPtrList abortinfo;
  char *longest_abort_info;
  long long longest_abort_info_time;
  struct FXCache recent_reads_cache;
};

/* 'global_cur_time' is normally a multiple of 2, except when we turn
   a transaction inevitable: we then add 1 to it. */
static volatile revision_t global_cur_time = 2;
static volatile revision_t next_locked_value = LOCKED + 3;   /* always odd */
static __thread struct tx_descriptor *thread_descriptor = NULL;

/* a multi-reader, single-writer lock: transactions normally take a reader
   lock, so don't conflict with each other; when we need to do a global GC,
   we take a writer lock to "stop the world".  Note the initializer here,
   which should give the correct priority for reached_safe_point(). */
static pthread_rwlock_t rwlock_in_transaction =
         PTHREAD_RWLOCK_WRITER_NONRECURSIVE_INITIALIZER_NP;

/************************************************************/

static void ValidateNow(struct tx_descriptor *);
static void CancelLocks(struct tx_descriptor *d);
static void AbortTransaction(int num);
static void SpinLoop(int num);
static gcptr Localize(struct tx_descriptor *d, gcptr R);

static _Bool is_inevitable(struct tx_descriptor *d)
{
  /* Assert that we are running a transaction.
   *      Returns True if this transaction is inevitable. */
  assert(d->active == 1 + !d->setjmp_buf);
  return d->active == 2;
}

static pthread_mutex_t mutex_inevitable = PTHREAD_MUTEX_INITIALIZER;
#define inev_mutex_acquire()  pthread_mutex_lock(&mutex_inevitable)
#define inev_mutex_release()  pthread_mutex_unlock(&mutex_inevitable)

/************************************************************/

static inline void PossiblyUpdateChain(
        struct tx_descriptor *d,
        gcptr G, gcptr R, gcptr R_Container, size_t offset)
{
  if (R != G && --d->readonly_updates < 0)
    {
      volatile revision_t *vp;
      d->readonly_updates = 148;   /* XXX tweak */
      // compress the chain one step (cannot compress the whole chain!)
      // avoid emitting a pointless "write", too.
      vp = (volatile revision_t *)&G->h_revision;
      if (*vp != (revision_t)R)
        *vp = (revision_t)R;
      // update the original field
      if (R_Container != NULL)
        {
          gcptr *ref = (gcptr *)(((char *)R_Container) + offset);
          *ref = R;
        }
    }
}

static gcptr LatestGlobalRevision(struct tx_descriptor *d, gcptr G,
                                  gcptr R_Container, size_t offset)
{
  gcptr R = G;
  revision_t v;
  volatile revision_t *vp;
 retry:
  while (1)
    {
      vp = (volatile revision_t *)&R->h_revision;
      v = *vp;
      if (v & 1)  // "is not a pointer", i.e.
        break;    //      "doesn't have a more recent revision"
      R = (gcptr)v;
    }
  if (__builtin_expect(v > d->start_time, 0))   // object too recent?
    {
      if (v >= LOCKED)
        {
          SpinLoop(1);     // spinloop until it is no longer LOCKED
          goto retry;
        }
      ValidateNow(d);                  // try to move start_time forward
      goto retry;                      // restart searching from R
    }
  PossiblyUpdateChain(d, G, R, R_Container, offset);
  return R;
}

static inline gcptr AddInReadSet(struct tx_descriptor *d, gcptr R)
{
  d->count_reads++;
  if (!fxcache_add(&d->recent_reads_cache, R)) {
      /* not in the cache: it may be the first time we see it,
       * so insert it into the list */
      gcptrlist_insert(&d->list_of_read_objects, R);
  }
      //      break;

      //  case 2:
      /* already in the cache, and FX_THRESHOLD reached */
      //      return Localize(d, R);
      //  }
  return R;
}

static inline gcptr _direct_read_barrier(gcptr G, gcptr R_Container,
                                         size_t offset)
{
  gcptr R;
  struct tx_descriptor *d = thread_descriptor;
  assert(d->active);
  if (!(G->h_tid & GCFLAG_POSSIBLY_OUTDATED))
    {
      R = G;
    }
  else
    {
      R = LatestGlobalRevision(d, G, R_Container, offset);
      if (R->h_tid & GCFLAG_POSSIBLY_OUTDATED)
        {
          wlog_t *entry;
          gcptr L;
          G2L_FIND(d->global_to_local, R, entry, goto not_found);
          L = entry->val;
          assert(L->h_revision == (revision_t)R);
          if (R_Container && !(R_Container->h_tid & GCFLAG_GLOBAL))
            {    /* R_Container is a local object */
              gcptr *ref = (gcptr *)(((char *)R_Container) + offset);
              *ref = L;   /* fix in-place */
            }
          return L;

        not_found:;
        }
    }
  R = AddInReadSet(d, R);
  return R;
}

void *stm_DirectReadBarrier(void *G1)
{
  return _direct_read_barrier((gcptr)G1, NULL, 0);
}

void *stm_DirectReadBarrierFromR(void *G1, void *R_Container1, size_t offset)
{
  return _direct_read_barrier((gcptr)G1, (gcptr)R_Container1, offset);
}

void *stm_RepeatReadBarrier(void *O1)
{
  // LatestGlobalRevision(O) would either return O or abort
  // the whole transaction, so omitting it is not wrong
  struct tx_descriptor *d = thread_descriptor;
  gcptr O = (gcptr)O1;
  gcptr L;
  wlog_t *entry;
  G2L_FIND(d->global_to_local, O, entry, return O);
  L = entry->val;
  assert(L->h_revision == (revision_t)O);
  return L;
}

#if 0
gcptr _NonTransactionalReadBarrier(gcptr P)
{
  /* testing only: use this outside transactions to check the state */
  revision_t v;
  struct tx_descriptor *d = thread_descriptor;
  assert(d == NULL || !d->active);

  assert(P->h_tid & GCFLAG_GLOBAL);

  while (!((v = P->h_revision) & 1))   // "is a pointer", i.e.
    {                                  //   "has a more recent revision"
      assert(P->h_tid & GCFLAG_POSSIBLY_OUTDATED);
      fprintf(stderr, "[%p->%p]\n", P, (gcptr)v);
      P = (gcptr)v;
    }
  if (P->h_tid & GCFLAG_POSSIBLY_OUTDATED)
    fprintf(stderr, "[---%p possibly outdated---]\n", P);
  return P;
}
#endif

static gcptr Localize(struct tx_descriptor *d, gcptr R)
{
  wlog_t *entry;
  gcptr L;
  G2L_FIND(d->global_to_local, R, entry, goto not_found);
  L = entry->val;
  assert(L->h_revision == (revision_t)R);
  return L;

 not_found:
  L = pypy_g__stm_duplicate(R);
  assert(!(L->h_tid & GCFLAG_GLOBAL));   /* must be removed by stm_duplicate */
  assert(!(L->h_tid & GCFLAG_POSSIBLY_OUTDATED));    /* must be removed by ^ */
  assert(L->h_tid & GCFLAG_LOCAL_COPY);    /* must be added by stm_duplicate */
  assert(L->h_tid & GCFLAG_NOT_WRITTEN); /* must not be set in the 1st place */
  L->h_revision = (revision_t)R;     /* back-reference to the original */
  g2l_insert(&d->global_to_local, R, L);
  d->count_reads++;
  gcptrlist_insert(&d->list_of_read_objects, R);
  return L;
}

void *stm_WriteBarrier(void *P1)
{
  gcptr P = (gcptr)P1;
  gcptr R, W;
  if (!(P->h_tid & GCFLAG_GLOBAL))
    {
      W = P;
      R = (gcptr)W->h_revision;
    }
  else
    {
      struct tx_descriptor *d = thread_descriptor;
      assert(d->active);
      if (P->h_tid & GCFLAG_POSSIBLY_OUTDATED)
        R = LatestGlobalRevision(d, P, NULL, 0);
      else
        R = P;
      W = Localize(d, R);
    }
  W->h_tid &= ~GCFLAG_NOT_WRITTEN;
  R->h_tid |= GCFLAG_POSSIBLY_OUTDATED;
  return W;
}

void *stm_WriteBarrierFromReady(void *R1)
{
  gcptr R = (gcptr)R1;
  gcptr W;
  if (!(R->h_tid & GCFLAG_GLOBAL))
    {
      W = R;
      R = (gcptr)W->h_revision;
    }
  else
    {
      struct tx_descriptor *d = thread_descriptor;
      assert(d->active);
      W = Localize(d, R);
    }
  W->h_tid &= ~GCFLAG_NOT_WRITTEN;
  R->h_tid |= GCFLAG_POSSIBLY_OUTDATED;
  return W;
}

/************************************************************/

static revision_t GetGlobalCurTime(struct tx_descriptor *d)
{
  assert(!is_inevitable(d));    // must not be myself inevitable
  return global_cur_time & ~1;
}

static _Bool ValidateDuringTransaction(struct tx_descriptor *d,
                                       _Bool during_commit)
{
  long i, size = d->list_of_read_objects.size;
  gcptr *items = d->list_of_read_objects.items;

  for (i=0; i<size; i++)
    {
      gcptr R = items[i];
      revision_t v;
      volatile revision_t *vp;
    retry:
      vp = (volatile revision_t *)&R->h_revision;
      v = *vp;
      if (!(v & 1))               // "is a pointer", i.e.
        return 0;                 //   "has a more recent revision"
      if (v >= LOCKED)            // locked
        {
          if (!during_commit)
            {
              assert(v != d->my_lock);    // we don't hold any lock
              SpinLoop(3);
              goto retry;
            }
          else
            {
              if (v != d->my_lock)         // not locked by me: conflict
                return 0;
            }
        }
    }
  return 1;
}

static void ValidateNow(struct tx_descriptor *d)
{
  d->start_time = GetGlobalCurTime(d);   // copy from the global time
  if (!ValidateDuringTransaction(d, 0))
    AbortTransaction(1);
}

/************************************************************/

static void SpinLoop(int num)
{
  struct tx_descriptor *d = thread_descriptor;
  assert(d->active);
  assert(num < SPINLOOP_REASONS);
  d->num_spinloops[num]++;
  spinloop();
}

size_t _stm_decode_abort_info(struct tx_descriptor *d, long long elapsed_time,
                              int abort_reason, char *output);

static void AbortTransaction(int num)
{
  struct tx_descriptor *d = thread_descriptor;
  unsigned long limit;
  size_t size;
  struct timespec now;
  long long elapsed_time;
  int err;

  assert(d->active);
  assert(!is_inevitable(d));
  assert(num < ABORT_REASONS);
  d->num_aborts[num]++;

  CancelLocks(d);

  /* compute the elapsed time */
  if (d->start_real_time.tv_nsec != -1 &&
      clock_gettime(CLOCK_MONOTONIC, &now) >= 0) {
    elapsed_time = now.tv_sec - d->start_real_time.tv_sec;
    elapsed_time *= 1000000000;
    elapsed_time += now.tv_nsec - d->start_real_time.tv_nsec;
    if (elapsed_time < 1)
      elapsed_time = 1;
  }
  else {
    elapsed_time = 1;
  }

  if (elapsed_time >= d->longest_abort_info_time)
    {
      /* decode the 'abortinfo' and produce a human-readable summary in
         the string 'longest_abort_info' */
      size = _stm_decode_abort_info(d, elapsed_time, num, NULL);
      free(d->longest_abort_info);
      d->longest_abort_info = malloc(size);
      if (d->longest_abort_info == NULL)
        d->longest_abort_info_time = 0;   /* out of memory! */
      else
        {
          if (_stm_decode_abort_info(d, elapsed_time,
                                     num, d->longest_abort_info) != size)
            {
              fprintf(stderr,
                      "during stm abort: object mutated unexpectedly\n");
              abort();
            }
          d->longest_abort_info_time = elapsed_time;
        }
    }

  /* run the undo log in reverse order, cancelling the values set by
     stm_ThreadLocalRef_LLSet(). */
  if (d->undolog.size > 0) {
      gcptr *item = d->undolog.items;
      long i;
      for (i=d->undolog.size; i>=0; i-=2) {
          void **addr = (void **)(item[i-2]);
          void *oldvalue = (void *)(item[i-1]);
          *addr = oldvalue;
      }
  }

  /* upon abort, set the reads size limit to 94% of how much was read
     so far.  This should ensure that, assuming the retry does the same
     thing, it will commit just before it reaches the conflicting point.
     Note that we should never *increase* the read length limit here. */
  limit = d->count_reads;
  if (limit > d->reads_size_limit_nonatomic) {  /* can occur if atomic */
      limit = d->reads_size_limit_nonatomic;
  }
  if (limit > 0) {
      limit -= (limit >> 4);
      d->reads_size_limit_nonatomic = limit;
  }

  gcptrlist_clear(&d->list_of_read_objects);
  gcptrlist_clear(&d->gcroots);
  g2l_clear(&d->global_to_local);

#ifdef RPY_STM_DEBUG_PRINT
  PYPY_DEBUG_START("stm-abort");
  if (PYPY_HAVE_DEBUG_PRINTS)
      fprintf(PYPY_DEBUG_FILE, "thread %lx aborting %d\n",
                               (long)d->my_lock, num);
  PYPY_DEBUG_STOP("stm-abort");
#endif

  // notifies the CPU that we're potentially in a spin loop
  SpinLoop(0);
  // jump back to the setjmp_buf (this call does not return)
  d->active = 0;
  err = pthread_rwlock_unlock(&rwlock_in_transaction);
  assert(err == 0);
  longjmp(*d->setjmp_buf, 1);
}

/************************************************************/

static void update_reads_size_limit(struct tx_descriptor *d)
{
  /* 'reads_size_limit' is set to ULONG_MAX if we are atomic; else
     we copy the value from reads_size_limit_nonatomic. */
  d->reads_size_limit = d->atomic ? ULONG_MAX : d->reads_size_limit_nonatomic;
}

static void init_transaction(struct tx_descriptor *d)
{
  int err;
  assert(d->active == 0);
  err = pthread_rwlock_rdlock(&rwlock_in_transaction);
  assert(err == 0);

  if (clock_gettime(CLOCK_MONOTONIC, &d->start_real_time) < 0) {
    d->start_real_time.tv_nsec = -1;
  }
  assert(d->list_of_read_objects.size == 0);
  assert(d->gcroots.size == 0);
  assert(!g2l_any_entry(&d->global_to_local));
  d->count_reads = 1;
  fxcache_clear(&d->recent_reads_cache);
  gcptrlist_clear(&d->undolog);
  gcptrlist_clear(&d->abortinfo);
}

void BeginTransaction(jmp_buf* buf)
{
  struct tx_descriptor *d = thread_descriptor;
  init_transaction(d);
  d->active = 1;
  d->setjmp_buf = buf;
  d->start_time = GetGlobalCurTime(d);
  update_reads_size_limit(d);
}

static void AcquireLocks(struct tx_descriptor *d)
{
  revision_t my_lock = d->my_lock;
  gcptr *item = d->gcroots.items;
  // gcroots should be sorted in some deterministic order by construction

  while (item[0] != NULL)
    {
      gcptr R = (gcptr)item[0]->h_revision;
      revision_t v;
      volatile revision_t *vp;
    retry:
      vp = (volatile revision_t *)&R->h_revision;
      v = *vp;
      if (!(v & 1))            // "is a pointer", i.e.
        AbortTransaction(0);   //   "has a more recent revision"
      if (v >= LOCKED)         // already locked by someone else
        {
          // we can always spinloop here: deadlocks should be impossible,
          // because FindRootsForLocalCollect's G2L_LOOP_FORWARD should
          // ensure a consistent ordering of the R's.
          SpinLoop(2);
          goto retry;
        }
      if (!bool_cas(vp, v, my_lock))
        goto retry;

      item[1] = (gcptr)v;
      item += 2;
    }
}

static void CancelLocks(struct tx_descriptor *d)
{
  long i, lastitem = d->gcroots.size - 2;
  gcptr *items = d->gcroots.items;
  for (i=0; i<=lastitem; i+=2)
    {
      gcptr R = (gcptr)items[i]->h_revision;
      revision_t v = (revision_t)items[i+1];
      if (v == 0)
        break;
      R->h_revision = v;
      // if we're going to retry later, and abort,
      // then we must not re-cancel the same entries
      items[i+1] = (gcptr)0;
    }
}

static void UpdateChainHeads(struct tx_descriptor *d, revision_t cur_time)
{
  gcptr *item, *itemstart = d->gcroots.items;
  revision_t new_revision = cur_time + 1;     // make an odd number
  assert(new_revision & 1);

  for (item = itemstart; item[0] != NULL; item += 2)
    {
      gcptr L = item[0];
      assert((L->h_tid & (GCFLAG_GLOBAL |
                          GCFLAG_NOT_WRITTEN |
                          GCFLAG_POSSIBLY_OUTDATED)) ==
              (GCFLAG_GLOBAL | GCFLAG_NOT_WRITTEN));
      item[1] = (gcptr)L->h_revision;    /* old value: pointer to R */
      L->h_revision = new_revision;
    }
  smp_wmb();
  for (item = itemstart; item[0] != NULL; item += 2)
    {
      gcptr L = item[0];
      gcptr R = item[1];
      assert((R->h_tid & (GCFLAG_GLOBAL |
                          GCFLAG_NOT_WRITTEN |
                          GCFLAG_POSSIBLY_OUTDATED)) ==
              (GCFLAG_GLOBAL | GCFLAG_NOT_WRITTEN | GCFLAG_POSSIBLY_OUTDATED));
      R->h_revision = (revision_t)L;
    }
}

static void FindRootsForLocalCollect(struct tx_descriptor *d)
{
  wlog_t *item;
  assert(d->gcroots.size == 0);

  G2L_LOOP_FORWARD(d->global_to_local, item)
    {
      gcptr R = item->addr;
      gcptr L = item->val;
      assert(L->h_revision == (revision_t)R);
      assert((L->h_tid & GCFLAG_GLOBAL) == 0);
      assert(L->h_tid & GCFLAG_LOCAL_COPY);
      assert((L->h_tid & GCFLAG_POSSIBLY_OUTDATED) == 0);

      /* GCFLAG_VISITED is only used by stmgc, but it's convenient to
       * remove that flag from here */
      L->h_tid &= ~(GCFLAG_VISITED | GCFLAG_LOCAL_COPY);
      if (L->h_tid & GCFLAG_NOT_WRITTEN)
        {
          L->h_tid |= GCFLAG_GLOBAL | GCFLAG_POSSIBLY_OUTDATED;
        }
      else
        {
          L->h_tid |= GCFLAG_GLOBAL | GCFLAG_NOT_WRITTEN;
          gcptrlist_insert2(&d->gcroots, L, (gcptr)0);
        }

    } G2L_LOOP_END;
  gcptrlist_insert(&d->gcroots, NULL);
  g2l_clear(&d->global_to_local);
}

#if 0
int _FakeReach(gcptr P)
{
  if (P->h_tid & GCFLAG_GLOBAL)
    return 0;
  P->h_tid |= GCFLAG_GLOBAL | GCFLAG_NOT_WRITTEN;
  if ((P->h_tid & GCFLAG_LOCAL_COPY) == 0)
    P->h_revision = 1;
  else
    P->h_tid &= ~GCFLAG_LOCAL_COPY;
  return 1;
}
#endif

void CommitTransaction(void)
{
  revision_t cur_time;
  struct tx_descriptor *d = thread_descriptor;
  int err;
  assert(d->active != 0);

  FindRootsForLocalCollect(d);
  AcquireLocks(d);

  if (is_inevitable(d))
    {
      // no-one else can have changed global_cur_time if I'm inevitable
      cur_time = d->start_time;
      if (!bool_cas(&global_cur_time, cur_time + 1, cur_time + 2))
        {
          assert(!"global_cur_time modified even though we are inev.");
          abort();
        }
      inev_mutex_release();
    }
  else
    {
      while (1)
        {
          cur_time = global_cur_time;
          if (cur_time & 1)
            {                    // there is another inevitable transaction
              CancelLocks(d);
              inev_mutex_acquire();   // wait until released
              inev_mutex_release();
              AcquireLocks(d);
              continue;
            }
          if (bool_cas(&global_cur_time, cur_time, cur_time + 2))
            break;
        }
      // validate (but skip validation if nobody else committed)
      if (cur_time != d->start_time)
        if (!ValidateDuringTransaction(d, 1))
          AbortTransaction(2);
    }
  /* we cannot abort any more from here */
  d->setjmp_buf = NULL;
  gcptrlist_clear(&d->list_of_read_objects);

  UpdateChainHeads(d, cur_time);

  gcptrlist_clear(&d->gcroots);
  d->num_commits++;
  d->active = 0;
  err = pthread_rwlock_unlock(&rwlock_in_transaction);
  assert(err == 0);
}

/************************************************************/

static void make_inevitable(struct tx_descriptor *d)
{
  d->setjmp_buf = NULL;
  d->active = 2;
  d->reads_size_limit_nonatomic = 0;
  update_reads_size_limit(d);
}

static revision_t acquire_inev_mutex_and_mark_global_cur_time(void)
{
  revision_t cur_time;

  inev_mutex_acquire();
  while (1)
    {
      cur_time = global_cur_time;
      assert((cur_time & 1) == 0);
      if (bool_cas(&global_cur_time, cur_time, cur_time + 1))
        break;
      /* else try again */
    }
  return cur_time;
}

void BecomeInevitable(const char *why)
{
  revision_t cur_time;
  struct tx_descriptor *d = thread_descriptor;
  if (d == NULL || d->active != 1)
    return;  /* I am already inevitable, or not in a transaction at all
                (XXX statically we should know when we're outside
                a transaction) */

#ifdef RPY_STM_DEBUG_PRINT
  PYPY_DEBUG_START("stm-inevitable");
  if (PYPY_HAVE_DEBUG_PRINTS)
    {
      fprintf(PYPY_DEBUG_FILE, "%s\n", why);
    }
#endif

  cur_time = acquire_inev_mutex_and_mark_global_cur_time();
  if (d->start_time != cur_time)
    {
      d->start_time = cur_time;
      if (!ValidateDuringTransaction(d, 0))
        {
          global_cur_time = cur_time;   // revert from (cur_time + 1)
          inev_mutex_release();
          AbortTransaction(3);
        }
    }
  make_inevitable(d);    /* cannot abort any more */

#ifdef RPY_STM_DEBUG_PRINT
  PYPY_DEBUG_STOP("stm-inevitable");
#endif
}

void BeginInevitableTransaction(void)
{
  struct tx_descriptor *d = thread_descriptor;
  revision_t cur_time;

  init_transaction(d);
  cur_time = acquire_inev_mutex_and_mark_global_cur_time();
  d->start_time = cur_time;
  make_inevitable(d);
}

/************************************************************/

inline static _Bool _PtrEq_Globals(gcptr G1, gcptr G2)
{
  /* This is a mess, because G1 and G2 can be different pointers to "the
     same" object, and it's hard to determine that.  Description of the
     idealized problem: we have chained lists following the 'h_revision'
     field from G1 and from G2, and we must return True if the chained
     lists end in the same object G and False if they don't.

     It's possible that G1 != G2 but G1->h_revision == G2->h_revision.
     This occurs because of random updates done by PossiblyUpdateChain().

     But the real mess comes from other threads doing concurrent
     updates.  They can be either done by PossiblyUpdateChain() from
     other threads, changing 'h_revision' without warning to point to
     what used to be 'h_revision-> ... -> h_revision'.  Alternatively,
     they can be adding new objects to the so-far root of the tree:
     consider the G that used to be the end of both chained lists.  Its
     'h_revision' used to be not-a-pointer.  But it can suddenly
     suddenly turns into a LOCK value, and then later to a pointer to
     some new object, making the chained list longer.  Worse, once the
     list is longer, a PossiblyUpdateChain() might make shortcuts in
     it...

     So it means even the following algorithm is flawed: "follow
     h_revisions from G1 until we reach G; then follow h_revisions from
     G2, and return True/False if we reach/do not reach the same G".

     For now we go with: try to move forward G1 and G2 alternatively,
     until we failed three times to move forward one of these.  Let's
     say the last three steps were "G1 is already at the end", "G2 is
     already at the end", "G1 is already at the end".  Then we can
     return (G1 == G2).  This is because we know that G1 was at the end
     of the chained list for the whole time during which we checked G2.

     WARNING: THIS ONLY WORKS ON THE X86 MEMORY MODEL, AND NOT ON WEAKER
     MODELS!
  */
  int blocked_steps = 0;
  volatile revision_t *vp;
  revision_t v;
  gcptr G3;

  while (1)
    {
      /* try to move G1 forward */
      vp = (volatile revision_t *)&G1->h_revision;
      v = *vp;
      if (v & 1)
        {
          blocked_steps++;
          if (blocked_steps == 3)
            break;
        }
      else
        {
          G1 = (gcptr)v;    /* success */
          blocked_steps = 0;
        }
      /* swap the roles of G1 and G2, then loop */
      G3 = G1; G1 = G2; G2 = G3;
    }
  return G1 == G2;
}

_Bool stm_PtrEq(gcptr P1, gcptr P2)
{
  if (P1 == P2)
    return 1;
  else if (P1 == NULL || P2 == NULL)   /* and not P1 == P2 == NULL */
    return 0;

  if (P1->h_tid & GCFLAG_GLOBAL)
    {
      if (P2->h_tid & GCFLAG_GLOBAL)
        return _PtrEq_Globals(P1, P2);
      else if (P2->h_tid & GCFLAG_LOCAL_COPY)
        return _PtrEq_Globals(P1, (gcptr)P2->h_revision);
      else
        return 0;   /* P1 is global, P2 is new */
    }
  /* P1 is local, i.e. either new or a local copy */
  if (P2->h_tid & GCFLAG_GLOBAL)
    {
      if (P1->h_tid & GCFLAG_LOCAL_COPY)
        return _PtrEq_Globals((gcptr)P1->h_revision, P2);
      else
        return 0;   /* P1 is new, P2 is global */
    }
  /* P1 and P2 are both locals (and P1 != P2) */
  return 0;
}

/************************************************************/

void stm_ThreadLocalRef_LLSet(void **addr, void *newvalue)
{
  struct tx_descriptor *d = thread_descriptor;
  gcptrlist_insert2(&d->undolog, (gcptr)addr, (gcptr)*addr);
  *addr = newvalue;
}

/************************************************************/

int DescriptorInit(void)
{
  if (thread_descriptor == NULL)
    {
      struct tx_descriptor *d = malloc(sizeof(struct tx_descriptor));
      memset(d, 0, sizeof(struct tx_descriptor));

#ifdef RPY_STM_DEBUG_PRINT
      PYPY_DEBUG_START("stm-init");
#endif

      /* initialize 'my_lock' to be a unique odd number >= LOCKED */
      while (1)
        {
          d->my_lock = next_locked_value;
          if (bool_cas(&next_locked_value, d->my_lock, d->my_lock + 2))
            break;
        }
      if (d->my_lock < LOCKED || d->my_lock == (revision_t)-1)
        {
          /* XXX fix this limitation */
          fprintf(stderr, "XXX error: too many threads ever created "
                          "in this process");
          abort();
        }
      assert(d->my_lock & 1);
      thread_descriptor = d;

#ifdef RPY_STM_DEBUG_PRINT
      if (PYPY_HAVE_DEBUG_PRINTS)
        fprintf(PYPY_DEBUG_FILE, "thread %lx starting (pthread=%lx)\n",
                (long)d->my_lock, (long)pthread_self());
      PYPY_DEBUG_STOP("stm-init");
#endif
      return 1;
    }
  else
    return 0;
}

void DescriptorDone(void)
{
  struct tx_descriptor *d = thread_descriptor;
  assert(d != NULL);
  assert(d->active == 0);

  thread_descriptor = NULL;

#ifdef RPY_STM_DEBUG_PRINT
  PYPY_DEBUG_START("stm-done");
  if (PYPY_HAVE_DEBUG_PRINTS) {
    int num_aborts = 0, num_spinloops = 0;
    int i;
    char line[256], *p = line;

    for (i=0; i<ABORT_REASONS; i++)
      num_aborts += d->num_aborts[i];
    for (i=0; i<SPINLOOP_REASONS; i++)
      num_spinloops += d->num_spinloops[i];

    p += sprintf(p, "thread %lx: %d commits, %d aborts\n",
                 (long)d->my_lock,
                 d->num_commits,
                 num_aborts);

    for (i=0; i<ABORT_REASONS; i++)
      p += sprintf(p, "%c%d", i == 0 ? '[' : ',',
                   d->num_aborts[i]);

    for (i=1; i<SPINLOOP_REASONS; i++)  /* num_spinloops[0] == num_aborts */
      p += sprintf(p, "%c%d", i == 1 ? '|' : ',',
                   d->num_spinloops[i]);

    p += sprintf(p, "]\n");
    fwrite(line, 1, p - line, PYPY_DEBUG_FILE);
  }
  PYPY_DEBUG_STOP("stm-done");
#endif

  free(d);
}

#include "rpyintf.c"
