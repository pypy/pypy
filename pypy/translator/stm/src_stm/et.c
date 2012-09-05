/* -*- c-basic-offset: 2 -*- */

/* XXX assumes that time never wraps around (in a 'long'), which may be
 * correct on 64-bit machines but not on 32-bit machines if the process
 * runs for long enough.
 */

#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
#include <pthread.h>

#define RPY_STM_DEBUG_PRINT     1
#define PYPY_DEBUG_START(s)     fprintf(stderr, "start: %s\n", s)
#define PYPY_DEBUG_STOP(s)      fprintf(stderr, " stop: %s\n", s)
#define PYPY_HAVE_DEBUG_PRINTS  1
#define PYPY_DEBUG_FILE         stderr

#include "et.h"

/************************************************************/

typedef Unsigned revision_t;
#define INEVITABLE  ((revision_t)-1)
#define LOCKED  ((revision_t)-0x10000)

#include "atomic_ops.h"
#include "lists.c"

/************************************************************/

#define ABORT_REASONS 5
#define SPINLOOP_REASONS 3

struct tx_descriptor {
  jmp_buf *setjmp_buf;
  revision_t start_time;
  revision_t my_lock;
  long atomic;   /* 0 = not atomic, > 0 atomic */
  long reads_size_limit, reads_size_limit_nonatomic; /* see should_break_tr. */
  int active;    /* 0 = inactive, 1 = regular, 2 = inevitable */
  int readonly_updates;
  unsigned int num_commits;
  unsigned int num_aborts[ABORT_REASONS];
  unsigned int num_spinloops[SPINLOOP_REASONS];
  struct GcPtrList list_of_read_objects;
  struct GcPtrList gcroots;
  struct G2L global_to_local;
  struct FXCache recent_reads_cache;
};

struct gcroot_s {
    gcptr R, L;
    revision_t v;
};

static volatile revision_t global_cur_time = 2;              /* always even */
static volatile revision_t next_locked_value = LOCKED + 3;   /* always odd */
static __thread struct tx_descriptor *thread_descriptor = NULL;

/************************************************************/

static void ValidateDuringTransaction(struct tx_descriptor *);
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
      d->readonly_updates = 148;   /* XXX tweak */
      // compress the chain
      while ((gcptr)G->h_revision != R)
        {
          gcptr G_next = (gcptr)G->h_revision;
          G->h_revision = (revision_t)R;
          G = G_next;
        }
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
 retry:
  while (!((v = R->h_revision) & 1))   // "is a pointer", i.e.
    {                                  //   "has a more recent revision"
      R = (gcptr)v;
    }
  if (__builtin_expect(v > d->start_time, 0))   // object too recent?
    {
      if (v >= LOCKED)
        {
          SpinLoop(1);     // spinloop until it is no longer LOCKED
          goto retry;
        }
      ValidateDuringTransaction(d);    // try to move start_time forward
      goto retry;                      // restart searching from R
    }
  PossiblyUpdateChain(d, G, R, R_Container, offset);
  return R;
}

static inline gcptr AddInReadSet(struct tx_descriptor *d, gcptr R)
{
  switch (fxcache_add(&d->recent_reads_cache, R)) {

  case 0:
      /* not in the cache: it may be the first time we see it,
       * so insert it into the list */
      gcptrlist_insert(&d->list_of_read_objects, R);
      break;

  case 2:
      /* already in the cache, and FX_THRESHOLD reached */
      return Localize(d, R);
  }
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

gcptr _DirectReadBarrier(gcptr G)
{
  return _direct_read_barrier(G, NULL, 0);
}

gcptr _DirectReadBarrierFromR(gcptr G, gcptr R_Container, size_t offset)
{
  return _direct_read_barrier(G, R_Container, offset);
}

gcptr _RepeatReadBarrier(gcptr O)
{
  // LatestGlobalRevision(O) would either return O or abort
  // the whole transaction, so omitting it is not wrong
  struct tx_descriptor *d = thread_descriptor;
  wlog_t *entry;
  G2L_FIND(d->global_to_local, O, entry, return O);
  return entry->val;
}

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

static gcptr Localize(struct tx_descriptor *d, gcptr R)
{
  wlog_t *entry;
  gcptr L;
  G2L_FIND(d->global_to_local, R, entry, goto not_found);
  L = entry->val;
  return L;

 not_found:
  L = pypy_g__stm_duplicate(R);
  L->h_tid &= ~(GCFLAG_GLOBAL | GCFLAG_POSSIBLY_OUTDATED);
  assert(L->h_tid & GCFLAG_NOT_WRITTEN);
  L->h_tid |= GCFLAG_LOCAL_COPY;
  L->h_revision = (revision_t)R;     /* back-reference to the original */
  g2l_insert(&d->global_to_local, R, L);
  return L;
}

gcptr _WriteBarrier(gcptr P)
{
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

gcptr _WriteBarrierFromReady(gcptr R)
{
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
  revision_t t;
  assert(!is_inevitable(d));    // must not be myself inevitable
  while (1)
    {
      t = global_cur_time;
      if (t != INEVITABLE)
        return t;
      // there is another transaction that is inevitable
      inev_mutex_acquire();     // wait until released
      inev_mutex_release();
      // retry
    }
}

static void ValidateDuringTransaction(struct tx_descriptor *d)
{

  long i, size = d->list_of_read_objects.size;
  gcptr *items = d->list_of_read_objects.items;

  assert(!is_inevitable(d));
  d->start_time = GetGlobalCurTime(d);   // copy from the global time

  for (i=0; i<size; i++)
    {
      gcptr R = items[i];
      revision_t v;
    retry:
      v = R->h_revision;
      if (!(v & 1))               // "is a pointer", i.e.
        AbortTransaction(1);      //   "has a more recent revision"
      if (v >= LOCKED)            // locked
        goto retry;
    }
}

static _Bool ValidateDuringCommit(struct tx_descriptor *d)
{
  long i, size = d->list_of_read_objects.size;
  gcptr *items = d->list_of_read_objects.items;
  revision_t my_lock = d->my_lock;

  for (i=0; i<size; i++)
    {
      gcptr R = items[i];
      revision_t v = R->h_revision;
      if (!(v & 1))               // "is a pointer", i.e.
        return 0;                 //   "has a more recent revision"
      if (v >= LOCKED)            // locked
        if (v != my_lock)         // and not by me
          return 0;               // XXX abort or spinloop??
    }
  return 1;
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

static void AbortTransaction(int num)
{
  struct tx_descriptor *d = thread_descriptor;
  assert(d->active);
  assert(!is_inevitable(d));
  assert(num < ABORT_REASONS);
  d->num_aborts[num]++;

  CancelLocks(d);

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
  longjmp(*d->setjmp_buf, 1);
}

/************************************************************/

static void update_reads_size_limit(struct tx_descriptor *d)
{
  /* 'reads_size_limit' is set to LONG_MAX if we are atomic; else
     we copy the value from reads_size_limit_nonatomic. */
  d->reads_size_limit = d->atomic ? LONG_MAX : d->reads_size_limit_nonatomic;
}

static void init_transaction(struct tx_descriptor *d)
{
  assert(d->active == 0);
  gcptrlist_clear(&d->list_of_read_objects);
  gcptrlist_clear(&d->gcroots);
  g2l_clear(&d->global_to_local);
  fxcache_clear(&d->recent_reads_cache);
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

#if 0
static int compare_by_R(const void *a, const void *b)
{
    gcptr Ra = *(const gcptr *)a;
    gcptr Rb = *(const gcptr *)b;
    if (Ra < Rb)
        return -1;
    else if (Ra == Rb)
        return 0;
    else
        return 1;
}
#endif

static void AcquireLocks(struct tx_descriptor *d)
{
  revision_t my_lock = d->my_lock;
  struct gcroot_s *item = (struct gcroot_s *)d->gcroots.items;
#if 0
  // gcroots should be sorted in some deterministic order by construction
  qsort(item, d->gcroots.size / 3, sizeof(struct gcroot_s), &compare_by_R);
#endif
  while (item->R != NULL)
    {
      gcptr R = item->R;
      revision_t v;
    retry:
      v = R->h_revision;
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
      if (!bool_cas((volatile revision_t *)&R->h_revision, v, my_lock))
        goto retry;

      item->v = v;
      item++;
    }
}

static void CancelLocks(struct tx_descriptor *d)
{
  long i, lastitem = d->gcroots.size - 3;
  gcptr *items = d->gcroots.items;
  for (i=0; i<=lastitem; i+=3)
    {
      gcptr R = items[i];
      gcptr v = items[i+2];
      if (v != 0)
        {
          R->h_revision = (revision_t)v;
          // if we're going to retry later, and abort,
          // then we must not re-cancel the same entries
          items[i+2] = 0;
        }
    }
}

static void UpdateChainHeads(struct tx_descriptor *d, revision_t cur_time)
{
  struct gcroot_s *item, *itemstart = (struct gcroot_s *)d->gcroots.items;
  revision_t new_revision = cur_time + 1;     // make an odd number
  assert(new_revision & 1);

  for (item = itemstart; item->R != NULL; item++)
    {
      gcptr L = item->L;
      assert((L->h_tid & (GCFLAG_GLOBAL |
                          GCFLAG_NOT_WRITTEN |
                          GCFLAG_POSSIBLY_OUTDATED)) ==
              (GCFLAG_GLOBAL | GCFLAG_NOT_WRITTEN));
      L->h_revision = new_revision;
    }
  smp_wmb();
  for (item = itemstart; item->R != NULL; item++)
    {
      gcptr L = item->L;
      gcptr R = item->R;
      assert((R->h_tid & (GCFLAG_GLOBAL |
                          GCFLAG_NOT_WRITTEN |
                          GCFLAG_POSSIBLY_OUTDATED)) ==
              (GCFLAG_GLOBAL | GCFLAG_NOT_WRITTEN | GCFLAG_POSSIBLY_OUTDATED));
      R->h_revision = (revision_t)L;
    }
}

static struct gcroot_s *FindRootsForLocalCollect(void)
{
  struct tx_descriptor *d = thread_descriptor;
  wlog_t *item;
  G2L_LOOP_FORWARD(d->global_to_local, item)
    {
      gcptr R = item->addr;
      gcptr L = item->val;
      if (L->h_tid & GCFLAG_NOT_WRITTEN)
        {
          assert(L->h_revision == (revision_t)R);
          L->h_tid |= GCFLAG_GLOBAL | GCFLAG_POSSIBLY_OUTDATED;
          continue;
        }
      gcptrlist_insert3(&d->gcroots, R, L, (gcptr)0);
    } G2L_LOOP_END;
  gcptrlist_insert(&d->gcroots, NULL);
  return (struct gcroot_s *)d->gcroots.items;
}

int _FakeReach(gcptr P)
{
  if (P->h_tid & GCFLAG_GLOBAL)
    return 0;
  P->h_tid |= GCFLAG_GLOBAL | GCFLAG_NOT_WRITTEN;
  if ((P->h_tid & GCFLAG_LOCAL_COPY) == 0)
    P->h_revision = 1;
  return 1;
}

void CommitTransaction(void)
{
  revision_t cur_time;
  struct tx_descriptor *d = thread_descriptor;
  assert(d->active != 0);
  if (d->gcroots.size == 0)
    FindRootsForLocalCollect();   /* for tests */

  AcquireLocks(d);

  if (is_inevitable(d))
    {
      // no-one else can have changed global_cur_time if I'm inevitable
      cur_time = d->start_time;
      if (!bool_cas(&global_cur_time, INEVITABLE, cur_time + 2))
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
          if (cur_time == INEVITABLE)
            {
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
        if (!ValidateDuringCommit(d))
          AbortTransaction(2);
    }
  UpdateChainHeads(d, cur_time);

  d->num_commits++;
  d->active = 0;
}

/************************************************************/

static void make_inevitable(struct tx_descriptor *d)
{
  d->setjmp_buf = NULL;
  d->active = 2;
  d->reads_size_limit_nonatomic = 0;
  update_reads_size_limit(d);
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

  inev_mutex_acquire();
  cur_time = global_cur_time;
  while (!bool_cas(&global_cur_time, cur_time, INEVITABLE))
    cur_time = global_cur_time;     /* try again */
  assert(cur_time != INEVITABLE);

  if (d->start_time != cur_time)
    {
      d->start_time = cur_time;
      if (!ValidateDuringCommit(d))
        {
          global_cur_time = cur_time;   // must restore the old value
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
  inev_mutex_acquire();
  cur_time = global_cur_time;
  while (!bool_cas(&global_cur_time, cur_time, INEVITABLE))
    cur_time = global_cur_time;     /* try again */
  assert(cur_time != INEVITABLE);
  d->start_time = cur_time;
  make_inevitable(d);
}

/************************************************************/

inline static gcptr GlobalizeForComparison(struct tx_descriptor *d, gcptr P)
{
  if (P != NULL && (P->h_tid & (GCFLAG_GLOBAL | GCFLAG_LOCAL_COPY)))
    {
      if (P->h_tid & GCFLAG_GLOBAL)
        P = LatestGlobalRevision(d, P, NULL, 0);
      else
        P = (gcptr)P->h_revision;    // return the original global obj
    }
  return P;
}

_Bool PtrEq(gcptr P1, gcptr P2)
{
  struct tx_descriptor *d = thread_descriptor;
  return GlobalizeForComparison(d, P1) == GlobalizeForComparison(d, P2);
}

/************************************************************/

void DescriptorInit(void)
{
  assert(thread_descriptor == NULL);
  if (1)
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
      if (d->my_lock < LOCKED)
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
    }
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
