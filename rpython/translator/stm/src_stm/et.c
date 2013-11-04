/* Imported by rpython/translator/stm/import_stmgc.py */
/* -*- c-basic-offset: 2 -*- */

/* XXX assumes that time never wraps around (in a 'long'), which may be
 * correct on 64-bit machines but not on 32-bit machines if the process
 * runs for long enough.
 */
#include "stmimpl.h"

char* stm_dbg_get_hdr_str(gcptr obj)
{
    static char tmp_buf[128];
    char *cur;
    char *flags[] = GC_FLAG_NAMES;
    int i;

    i = 0;
    cur = tmp_buf;
    cur += sprintf(cur, "%p : ", obj);
    while (flags[i]) {
        if (obj->h_tid & (STM_FIRST_GCFLAG << i)) {
            cur += sprintf(cur, "%s|", flags[i]);
        }
        i++;
    }
    cur += sprintf(cur, "tid=%ld", stm_get_tid(obj));
    cur += sprintf(cur, " : rev=0x%lx : orig=0x%lx", 
                   (long)obj->h_revision, (long)obj->h_original);
    return tmp_buf;
}

void stm_dump_dbg(void)
{
    fprintf(stderr, "/**** stm_dump_dbg ****/\n\n");

    int i;
    for (i = 0; i < MAX_THREADS; i++) {
        struct tx_public_descriptor *pd = stm_descriptor_array[i];
        if (pd == NULL)
            continue;
        fprintf(stderr, "stm_descriptor_array[%d]\n((struct tx_public_descriptor *)%p)\n",
                i, pd);

        struct tx_descriptor *d = stm_tx_head;
        while (d && d->public_descriptor != pd)
            d = d->tx_next;
        if (!d) {
            fprintf(stderr, "\n");
            continue;
        }

        fprintf(stderr, "((struct tx_descriptor *)\033[%dm%p\033[0m)\n"
                "pthread_self = 0x%lx\n\n", d->tcolor, d, (long)d->pthreadid);
    }

    fprintf(stderr, "/**********************/\n");
}


__thread int stm_active;
__thread struct tx_descriptor *thread_descriptor = NULL;

/* 'global_cur_time' is normally a multiple of 2, except when we turn
   a transaction inevitable: we then add 1 to it. */
static revision_t global_cur_time = 2;

/* a negative odd number that identifies the currently running
   transaction within the thread. */
__thread revision_t stm_private_rev_num;


revision_t stm_global_cur_time(void)  /* for tests */
{
  return global_cur_time;
}
revision_t get_private_rev_num(void)        /* for tests */
{
  return stm_private_rev_num;
}
struct tx_descriptor *stm_thread_descriptor(void)  /* for tests */
{
  return thread_descriptor;
}
static int is_private(gcptr P)
{
  return (P->h_revision == stm_private_rev_num) ||
    (P->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED);
}
int _stm_is_private(gcptr P)
{
  return is_private(P);
}
void stm_clear_read_cache(void)
{
  fxcache_clear(&thread_descriptor->recent_reads_cache);
}

/************************************************************/

static void ValidateNow(struct tx_descriptor *);
static void CancelLocks(struct tx_descriptor *d);

static _Bool is_inevitable(struct tx_descriptor *d)
{
  /* Assert that we are running a transaction.
   *      Returns True if this transaction is inevitable. */
  assert(*d->active_ref == 1 + !d->setjmp_buf);
  return *d->active_ref == 2;
}

static pthread_mutex_t mutex_inevitable = PTHREAD_MUTEX_INITIALIZER;

static void inev_mutex_release(void)
{
  pthread_mutex_unlock(&mutex_inevitable);
}

static void inev_mutex_acquire(struct tx_descriptor *d)
{   /* must save roots around this call */
  stm_stop_sharedlock();
  pthread_mutex_lock(&mutex_inevitable);
  stm_start_sharedlock();

  if (*d->active_ref < 0)
    {
      inev_mutex_release();
      AbortNowIfDelayed();
      abort();   /* unreachable */
    }
}

/************************************************************/

gcptr stm_DirectReadBarrier(gcptr G)
{
  struct tx_descriptor *d = thread_descriptor;
  gcptr P = G;
  revision_t v;

  d->count_reads++;
  assert(IMPLIES(!(P->h_tid & GCFLAG_OLD), stmgc_is_in_nursery(d, P)));

 restart_all:
  if (P->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED)
    {
      assert(IS_POINTER(P->h_revision));   /* pointer to the backup copy */

      /* check P->h_revision->h_revision: if a pointer, then it means
         the backup copy has been stolen into a public object and then
         modified by some other thread.  Abort. */
      if (IS_POINTER(((gcptr)P->h_revision)->h_revision))
        AbortTransaction(ABRT_STOLEN_MODIFIED);

      goto add_in_recent_reads_cache;
    }
  /* else, for the rest of this function, we can assume that P was not
     a private copy */

  if (P->h_tid & GCFLAG_PUBLIC)
    {
      /* follow the chained list of h_revision's as long as they are
         regular pointers.  We will only find more public objects
         along this chain.
      */
    restart_all_public:
      assert(P->h_tid & GCFLAG_PUBLIC);
      v = ACCESS_ONCE(P->h_revision);
      if (IS_POINTER(v))  /* "is a pointer", "has a more recent revision" */
        {
        retry:
          if (v & 2)
            goto follow_stub;

          gcptr P_prev = P;
          P = (gcptr)v;
          assert((P->h_tid & GCFLAG_PUBLIC) ||
                 (P_prev->h_tid & GCFLAG_MOVED));

          v = ACCESS_ONCE(P->h_revision);

          if (IS_POINTER(v))
            {
              if (v & 2)
                goto follow_stub;

              /* we update P_prev->h_revision as a shortcut */
              /* XXX check if this really gives a worse performance than only
                 doing this write occasionally based on a counter in d */
              P_prev->h_revision = v;
              P = (gcptr)v;
              v = ACCESS_ONCE(P->h_revision);
              if (IS_POINTER(v))
                goto retry;
            }

          /* We reach this point if P != G only.  Check again the
             read_barrier_cache: if P now hits the cache, just return it
          */
          if (FXCACHE_AT(P) == P)
            {
              dprintf(("read_barrier: %p -> %p fxcache\n", G, P));
              return P;
            }
        }

      /* If we land on a P with GCFLAG_PUBLIC_TO_PRIVATE, it might be
         because *we* have an entry in d->public_to_private.  (It might
         also be someone else.)
      */
      if (P->h_tid & GCFLAG_PUBLIC_TO_PRIVATE)
        {
          wlog_t *item;
        retry_public_to_private:;
          G2L_FIND(d->public_to_private, P, item, goto no_private_obj);

          /* We have a key in 'public_to_private'.  The value is the
             corresponding private object. */
          P = item->val;
          assert(!(P->h_tid & GCFLAG_PUBLIC));
          assert(is_private(P));
          dprintf(("read_barrier: %p -> %p public_to_private\n", G, P));
          return P;

        no_private_obj:
          /* Key not found.  It might be because there really is none, or
             because we still have it waiting in 'stolen_objects'. */
          if (d->public_descriptor->stolen_objects.size > 0)
            {
              spinlock_acquire(d->public_descriptor->collection_lock, 'N');
              stm_normalize_stolen_objects(d);
              spinlock_release(d->public_descriptor->collection_lock);
              goto retry_public_to_private;
            }
        }

      /* The answer is a public object.  Is it too recent? */
      if (UNLIKELY(v > d->start_time))
        {
          if (v >= LOCKED)
            {
              SpinLoop(SPLP_LOCKED_INFLIGHT);
              goto restart_all_public; // spinloop until it is no longer LOCKED
            }
          ValidateNow(d);                  // try to move start_time forward
          goto restart_all_public;         // restart searching from P
        }
      dprintf(("read_barrier: %p -> %p public\n", G, P));
    }
  else
    {
      /* Not private and not public: it's a protected object
       */
      dprintf(("read_barrier: %p -> %p protected\n", G, P));

      /* The risks are not high, but in parallel it's possible for the
         object to be stolen by another thread and become public, after
         which it can be outdated by another commit.  So the following
         assert can actually fail in that case. */
      /*assert(P->h_revision & 1);*/
    }

  dprintf(("readobj: %p\n", P));
  assert(!(P->h_tid & GCFLAG_STUB));
  gcptrlist_insert(&d->list_of_read_objects, P);

 add_in_recent_reads_cache:
  /* The risks are that the following assert fails, because the flag was
     added just now by a parallel thread during stealing... */
  /*assert(!(P->h_tid & GCFLAG_MOVED));*/
  fxcache_add(&d->recent_reads_cache, P);
  return P;

 follow_stub:;
  /* We know that P is a stub object, because only stubs can have
     an h_revision that is == 2 mod 4.
  */
  struct tx_public_descriptor *foreign_pd = STUB_THREAD(P);
  if (foreign_pd == d->public_descriptor)
    {
      /* Same thread: dereference the pointer directly.  It's possible
         we reach any kind of object, even a public object, in case it
         was stolen.  So we just repeat the whole procedure. */
      P = (gcptr)(v - 2);
      dprintf(("read_barrier: %p -> %p via stub\n  ", G, P));

      if (UNLIKELY((P->h_revision != stm_private_rev_num) &&
                   (FXCACHE_AT(P) != P)))
        goto restart_all;

      return P;
    }
  else
    {
      /* stealing */
      dprintf(("read_barrier: %p -> stealing %p...\n  ", G, P));
      stm_steal_stub(P);

      assert(P->h_tid & GCFLAG_PUBLIC);
      goto restart_all_public;
    }
}

gcptr stm_RepeatReadBarrier(gcptr P)
{
  /* Version of stm_DirectReadBarrier() that doesn't abort and assumes
   * that 'P' was already an up-to-date result of a previous
   * stm_DirectReadBarrier().  We only have to check if we did in the
   * meantime a stm_write_barrier().  Should only be called if we
   * have the flag PUBLIC_TO_PRIVATE or on MOVED objects.  This version
   * should never abort (it is used in stm_decode_abort_info()).
   */
  assert(P->h_tid & GCFLAG_PUBLIC);
  assert(!(P->h_tid & GCFLAG_STUB));
  assert(IMPLIES(!(P->h_tid & GCFLAG_OLD), 
                 stmgc_is_in_nursery(thread_descriptor, P)));


  if (P->h_tid & GCFLAG_MOVED)
    {
      dprintf(("repeat_read_barrier: %p -> %p moved\n", P,
               (gcptr)P->h_revision));
      P = (gcptr)P->h_revision;
      assert(P->h_tid & GCFLAG_PUBLIC);
      assert(!(P->h_tid & GCFLAG_STUB));
      assert(!(P->h_tid & GCFLAG_MOVED));
      if (!(P->h_tid & GCFLAG_PUBLIC_TO_PRIVATE))
        return P;
    }
  assert(P->h_tid & GCFLAG_PUBLIC_TO_PRIVATE);

  struct tx_descriptor *d = thread_descriptor;
  wlog_t *item;
  G2L_FIND(d->public_to_private, P, item, goto no_private_obj);

  /* We have a key in 'public_to_private'.  The value is the
     corresponding private object. */
  dprintf(("repeat_read_barrier: %p -> %p public_to_private\n", P, item->val));
  P = item->val;
  assert(!(P->h_tid & GCFLAG_PUBLIC));
  assert(!(P->h_tid & GCFLAG_STUB));
  assert(is_private(P));
  return P;

 no_private_obj:
  /* Key not found.  It should not be waiting in 'stolen_objects',
     because this case from steal.c applies to objects to were originally
     backup objects.  'P' cannot be a backup object if it was obtained
     earlier as a result of stm_read_barrier().
  */
  return P;
}

gcptr stm_ImmutReadBarrier(gcptr P)
{
  assert(P->h_tid & GCFLAG_STUB);
  assert(P->h_tid & GCFLAG_PUBLIC);
  assert(IMPLIES(!(P->h_tid & GCFLAG_OLD), 
                 stmgc_is_in_nursery(thread_descriptor, P)));


  revision_t v = ACCESS_ONCE(P->h_revision);
  assert(IS_POINTER(v));  /* "is a pointer", "has a more recent revision" */

  if (!(v & 2))
    {
      P = (gcptr)v;
    }
  else
    {
      /* follow a stub reference */
      struct tx_descriptor *d = thread_descriptor;
      struct tx_public_descriptor *foreign_pd = STUB_THREAD(P);
      if (foreign_pd == d->public_descriptor)
        {
          /* Same thread: dereference the pointer directly. */
          dprintf(("immut_read_barrier: %p -> %p via stub\n  ", P,
                   (gcptr)(v - 2)));
          P = (gcptr)(v - 2);
        }
      else
        {
          /* stealing: needed because accessing v - 2 from this thread
             is forbidden (the target might disappear under our feet) */
          dprintf(("immut_read_barrier: %p -> stealing...\n  ", P));
          stm_steal_stub(P);
        }
    }
  return stm_immut_read_barrier(P);   /* retry */
}

static gcptr _match_public_to_private(gcptr P, gcptr pubobj, gcptr privobj,
                                      int from_stolen)
{
  gcptr org_pubobj = pubobj;
  while ((pubobj->h_revision & 3) == 0)
    {
      assert(pubobj != P);
      pubobj = (gcptr)pubobj->h_revision;
    }
  if (pubobj == P || ((P->h_revision & 3) == 2 &&
                      pubobj->h_revision == P->h_revision))
    {
      assert(!(org_pubobj->h_tid & GCFLAG_STUB));
      assert(!(privobj->h_tid & GCFLAG_PUBLIC));
      assert(is_private(privobj));
      if (P != org_pubobj)
        dprintf(("| actually %p ", org_pubobj));
      if (from_stolen)
        dprintf(("-stolen"));
      else
        assert(org_pubobj->h_tid & GCFLAG_PUBLIC_TO_PRIVATE);
      dprintf(("-public_to_private-> %p private\n", privobj));
      return privobj;
    }
  return NULL;
}

static gcptr _find_public_to_private(gcptr P)
{
  gcptr R;
  wlog_t *item;
  struct tx_descriptor *d = thread_descriptor;

  G2L_LOOP_FORWARD(d->public_to_private, item)
    {
      assert(item->addr->h_tid & GCFLAG_PUBLIC_TO_PRIVATE);
      R = _match_public_to_private(P, item->addr, item->val, 0);
      if (R != NULL)
        return R;

    } G2L_LOOP_END;

  long i, size = d->public_descriptor->stolen_objects.size;
  gcptr *items = d->public_descriptor->stolen_objects.items;

  for (i = 0; i < size; i += 2)
    {
      if (items[i + 1] == NULL)
        continue;
      R = _match_public_to_private(P, items[i], items[i + 1], 1);
      if (R != NULL)
        return R;
    }

  return NULL;
}

static void _check_flags(gcptr P)
{
#ifndef NDEBUG
  struct tx_descriptor *d = thread_descriptor;
  if (P->h_tid & GCFLAG_STUB)
    {
      dprintf(("S"));
    }
  int is_old = (P->h_tid & GCFLAG_OLD) != 0;
  int in_nurs = (d->nursery_base <= (char*)P && ((char*)P) < d->nursery_end);
  if (in_nurs)
    {
      assert(!is_old);
      dprintf(("Y "));
    }
  else
    {
      assert(is_old);
      dprintf(("O "));
    }
#endif
}

gcptr _stm_nonrecord_barrier(gcptr P)
{
  /* follows the logic in stm_DirectReadBarrier() */
  struct tx_descriptor *d = thread_descriptor;
  revision_t v;

  dprintf(("_stm_nonrecord_barrier: %p ", P));
  _check_flags(P);

 restart_all:
  if (P->h_revision == stm_private_rev_num)
    {
      /* private */
      dprintf(("private\n"));
      return P;
    }

  if (P->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED)
    {
      /* private too, with a backup copy */
      assert(IS_POINTER(P->h_revision));
      dprintf(("private_from_protected\n"));
      return P;
    }

  if (P->h_tid & GCFLAG_PUBLIC)
    {
      dprintf(("public "));

      while (v = P->h_revision, IS_POINTER(v))
        {
          if (P->h_tid & GCFLAG_MOVED)
            dprintf(("nursery_moved "));

          if (v & 2)
            {
              dprintf(("stub "));
              gcptr L = _find_public_to_private(P);
              if (L != NULL)
                return L;
              goto follow_stub;
            }

          P = (gcptr)v;
          assert(P->h_tid & GCFLAG_PUBLIC);
          dprintf(("-> %p public ", P));
          _check_flags(P);
        }

      gcptr L = _find_public_to_private(P);
      if (L != NULL)
        return L;

      if (UNLIKELY(v > d->start_time))
        {
          dprintf(("too recent!\n"));
          return NULL;   // object too recent
        }
      dprintf(("\n"));
    }
  else
    {
      dprintf(("protected\n"));
    }
  return P;

 follow_stub:;
  if (STUB_THREAD(P) == d->public_descriptor)
    {
      P = (gcptr)(v - 2);
      dprintf(("-> %p ", P));
      _check_flags(P);
    }
  else
    {
      P = (gcptr)(v - 2);
      /* cannot _check_flags(P): foreign! */
      dprintf(("-foreign-> %p ", P));
      if (P->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED)
        {
          P = (gcptr)P->h_revision;     /* the backup copy */
          /* cannot _check_flags(P): foreign! */
          dprintf(("-backup-> %p ", P));
        }
      if (!(P->h_tid & GCFLAG_PUBLIC))
        {
          dprintf(("protected by someone else!\n"));
          return (gcptr)-1;
        }
    }
  /* cannot _check_flags(P): foreign! */
  goto restart_all;
}

static gcptr LocalizeProtected(struct tx_descriptor *d, gcptr P)
{
  gcptr B;

  assert(P->h_revision != stm_private_rev_num);
  assert(P->h_revision & 1);
  assert(!(P->h_tid & GCFLAG_PUBLIC_TO_PRIVATE));
  assert(!(P->h_tid & GCFLAG_BACKUP_COPY));
  assert(!(P->h_tid & GCFLAG_STUB));
  assert(!(P->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED));

  B = stmgc_duplicate_old(P);
  B->h_tid |= GCFLAG_BACKUP_COPY;
  B->h_tid &= ~GCFLAG_HAS_ID;
  if (!(P->h_original) && (P->h_tid & GCFLAG_OLD)) {
    /* if P is old, it must be the original
       if P is young, it will create a shadow original later
       or it's getting decided when backup gets stolen.
    */
    B->h_original = (revision_t)P;
  }
  
  P->h_tid |= GCFLAG_PRIVATE_FROM_PROTECTED;
  P->h_revision = (revision_t)B;

  gcptrlist_insert(&d->private_from_protected, P);
  dprintf(("private_from_protected: insert %p (backup %p)\n", P, B));

  return P;   /* always returns its arg: the object is converted in-place */
}

static gcptr LocalizePublic(struct tx_descriptor *d, gcptr R)
{
  assert(R->h_tid & GCFLAG_PUBLIC);
  assert(!(R->h_tid & GCFLAG_MOVED));

#ifdef _GC_DEBUG
  wlog_t *entry;
  G2L_FIND(d->public_to_private, R, entry, goto not_found);
  stm_fatalerror("R is already in public_to_private\n");
 not_found:
#endif

  assert(!(R->h_tid & GCFLAG_STUB));
  R->h_tid |= GCFLAG_PUBLIC_TO_PRIVATE;

  /* note that stmgc_duplicate() usually returns a young object, but may
     return an old one if the nursery is full at this moment. */
  gcptr L = stmgc_duplicate(R);
  if (!(L->h_original) || L->h_tid & GCFLAG_PREBUILT_ORIGINAL) {
    /* if we don't have an original object yet, it must be the 
       old public R 
       Also, prebuilt objects may have a predefined hash stored
       in the h_original. -> point to the original copy on copies
       of the prebuilt.
    */
    assert(R->h_tid & GCFLAG_OLD); // if not, force stm_id??
    L->h_original = (revision_t)R;
  }

  assert(!(L->h_tid & GCFLAG_BACKUP_COPY));
  assert(!(L->h_tid & GCFLAG_STUB));
  assert(!(L->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED));
  L->h_tid &= ~(GCFLAG_VISITED           |
                GCFLAG_MARKED            |
                GCFLAG_PUBLIC            |
                GCFLAG_PREBUILT_ORIGINAL |
                GCFLAG_PUBLIC_TO_PRIVATE |
                GCFLAG_WRITE_BARRIER     |
                0);
  L->h_revision = stm_private_rev_num;
  assert(stm_private_rev_num < 0);
  assert(stm_private_rev_num & 1);
  g2l_insert(&d->public_to_private, R, L);
  dprintf(("write_barrier: adding %p -> %p to public_to_private\n",
           R, L));

  /* must remove R from the read_barrier_cache, because returning R is no
     longer a valid result */
  fxcache_remove(&d->recent_reads_cache, R);

  return L;
}

static inline void record_write_barrier(gcptr P)
{
  assert(is_private(P));
  assert(IMPLIES(!(P->h_tid & GCFLAG_OLD),
                 stmgc_is_in_nursery(thread_descriptor, P)));
  if (P->h_tid & GCFLAG_WRITE_BARRIER)
    {
      assert(P->h_tid & GCFLAG_OLD);
      P->h_tid &= ~GCFLAG_WRITE_BARRIER;
      gcptrlist_insert(&thread_descriptor->old_objects_to_trace, P);
    }
}

gcptr stm_RepeatWriteBarrier(gcptr P)
{
  assert(IMPLIES(!(P->h_tid & GCFLAG_OLD), 
                 stmgc_is_in_nursery(thread_descriptor, P)));

  assert(!(P->h_tid & GCFLAG_IMMUTABLE));
  assert(is_private(P));
  assert(P->h_tid & GCFLAG_WRITE_BARRIER);
  P->h_tid &= ~GCFLAG_WRITE_BARRIER;
  gcptrlist_insert(&thread_descriptor->old_objects_to_trace, P);
  return P;
}

gcptr stm_WriteBarrier(gcptr P)
{
  assert(!(P->h_tid & GCFLAG_IMMUTABLE));
  assert((P->h_tid & GCFLAG_STUB) ||
         stmgc_size(P) > sizeof(struct stm_stub_s) - WORD);
  /* If stmgc_size(P) gives a number <= sizeof(stub)-WORD, then there is a
     risk of overrunning the object later in gcpage.c when copying a stub
     over it.  However such objects are so small that they contain no field
     at all, and so no write barrier should occur on them. */

  assert(IMPLIES(!(P->h_tid & GCFLAG_OLD), 
                 stmgc_is_in_nursery(thread_descriptor, P)));

  if (is_private(P))
    {
      /* If we have GCFLAG_WRITE_BARRIER in P, then list it into
         old_objects_to_trace: it's a private object that may be
         modified by the program after we return, and the mutation may
         be to write young pointers (in fact it's a common case).
      */
      record_write_barrier(P);
      return P;
    }

  gcptr R, W;
  R = stm_read_barrier(P);

  if (is_private(R))
    {
      record_write_barrier(R);
      return R;
    }

  struct tx_descriptor *d = thread_descriptor;
  assert(*d->active_ref >= 1);

  /* We need the collection_lock for the sequel; this is required notably
     because we're about to edit flags on a protected object.
  */
  spinlock_acquire(d->public_descriptor->collection_lock, 'L');
  if (d->public_descriptor->stolen_objects.size != 0)
    stm_normalize_stolen_objects(d);

  if (R->h_tid & GCFLAG_PUBLIC)
    {
      /* Make and return a new (young) private copy of the public R.
         Add R into the list 'public_with_young_copy', unless W is
         actually an old object, in which case we need to record W.
      */
      if (R->h_tid & GCFLAG_MOVED)
        {
          /* Bah, the object turned into this kind of stub, possibly
             while we were waiting for the collection_lock, because it
             was stolen by someone else.  Use R->h_revision instead. */
          assert(IS_POINTER(R->h_revision));
          R = (gcptr)R->h_revision;
          assert(R->h_tid & GCFLAG_PUBLIC);
        }
      assert(R->h_tid & GCFLAG_OLD);
      W = LocalizePublic(d, R);
      assert(is_private(W));

      if (W->h_tid & GCFLAG_OLD)
        gcptrlist_insert(&d->old_objects_to_trace, W);
      else
        gcptrlist_insert(&d->public_with_young_copy, R);
    }
  else
    {
      /* Turn the protected copy in-place into a private copy.  If it's
         an old object that still has GCFLAG_WRITE_BARRIER, then we must
         also record it in the list 'old_objects_to_trace'. */
      W = LocalizeProtected(d, R);
      assert(is_private(W));
      record_write_barrier(W);
    }

  spinlock_release(d->public_descriptor->collection_lock);

  dprintf(("write_barrier: %p -> %p -> %p\n", P, R, W));

  return W;
}

gcptr stm_get_private_from_protected(long index)
{
  struct tx_descriptor *d = thread_descriptor;
  if (index < gcptrlist_size(&d->private_from_protected))
    return d->private_from_protected.items[index];
  return NULL;
}

gcptr stm_get_read_obj(long index)
{
  struct tx_descriptor *d = thread_descriptor;
  if (index < gcptrlist_size(&d->list_of_read_objects))
    return d->list_of_read_objects.items[index];
  return NULL;
}

/************************************************************/

static revision_t GetGlobalCurTime(struct tx_descriptor *d)
{
  assert(!is_inevitable(d));    // must not be myself inevitable
  return ACCESS_ONCE(global_cur_time) & ~1;
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
    retry:
      v = ACCESS_ONCE(R->h_revision);
      if (IS_POINTER(v))  /* "is a pointer", i.e. has a more recent revision */
        {
          if (R->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED)
            {
              /* such an object R might be listed in list_of_read_objects
                 before it was turned from protected to private */
              if (((gcptr)v)->h_tid & GCFLAG_PUBLIC)
                {
                  /* The backup was stolen, but maybe not modified
                     afterwards.  Check it. */
                  R = (gcptr)v;
                  goto retry;
                }
              else
                {
                  /* The backup was not stolen, everything's fine */
                  continue;
                }
            }
          else if ((R->h_tid & (GCFLAG_PUBLIC | GCFLAG_MOVED))
                            == (GCFLAG_PUBLIC | GCFLAG_MOVED))
            {
              /* such an object is identical to the one it points to
               (stolen protected young object with h_revision pointing
               to the new copy) */
              R = (gcptr)v;
              goto retry;
            }
          else
            {
              dprintf(("validation failed: "
                       "%p has a more recent revision\n", R));
              return 0;
            }
        }
      if (v >= LOCKED)            // locked
        {
          if (!during_commit)
            {
              assert(v != d->my_lock);    // we don't hold any lock
              /* spinloop until the other thread releases its lock */
              SpinLoop(SPLP_LOCKED_VALIDATE);
              goto retry;
            }
          else
            {
              if (v != d->my_lock)         // not locked by me: conflict
                {
                  /* It's delicate here to do a spinloop rather than
                     just aborting.

                     A case that can occur: two threads A and B are both
                     committing, thread A locked object a, thread B
                     locked object b, and then thread A tries to
                     validate the reads it did on object b and
                     vice-versa.  In this case both threads cannot
                     commit, but if they both enter the SpinLoop()
                     here, then they will livelock.

                     Another case: thread A might be blocked in this
                     spinloop, while thread B is blocked in the
                     SpinLoop(SPLP_LOCKED_COMMIT) below.

                     For now we always abort.
                  */
                  dprintf(("validation failed: "
                           "%p is locked by another thread\n", R));
                  return 0;
                }
            }
        }
    }
  return 1;
}

static void ValidateNow(struct tx_descriptor *d)
{
  d->start_time = GetGlobalCurTime(d);   // copy from the global time
  dprintf(("et.c: ValidateNow: %ld\n", (long)d->start_time));

  /* subtle: we have to normalize stolen objects, because doing so
     might add a few extra objects in the list_of_read_objects */
  if (d->public_descriptor->stolen_objects.size != 0)
    {
      spinlock_acquire(d->public_descriptor->collection_lock, 'N');
      stm_normalize_stolen_objects(d);
      spinlock_release(d->public_descriptor->collection_lock);
    }

  if (!ValidateDuringTransaction(d, 0))
    AbortTransaction(ABRT_VALIDATE_INFLIGHT);
}

/************************************************************/

void SpinLoop(int num)
{
  struct tx_descriptor *d = thread_descriptor;
  assert(*d->active_ref >= 1);
  assert(num < SPINLOOP_REASONS);
  d->num_spinloops[num]++;
  smp_spinloop();
}

void stm_abort_and_retry(void)
{
    AbortTransaction(ABRT_MANUAL);
}

void AbortPrivateFromProtected(struct tx_descriptor *d);

void AbortTransaction(int num)
{
  static const char *abort_names[] = ABORT_NAMES;
  struct tx_descriptor *d = thread_descriptor;
  unsigned long limit;
  struct timespec now;
  long long elapsed_time;

  /* acquire the lock, but don't double-acquire it if already committing */
  if (d->public_descriptor->collection_lock != 'C')
    {
      spinlock_acquire(d->public_descriptor->collection_lock, 'C');
      if (d->public_descriptor->stolen_objects.size != 0)
        stm_normalize_stolen_objects(d);
      assert(!stm_has_got_any_lock(d));
    }
  else
    {
      CancelLocks(d);
      assert(!stm_has_got_any_lock(d));
    }

  assert(*d->active_ref != 0);
  assert(!is_inevitable(d));
  assert(num < ABORT_REASONS);
  d->num_aborts[num]++;

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
      size_t size = stm_decode_abort_info(d, elapsed_time, num, NULL);
      free(d->longest_abort_info);
      d->longest_abort_info = malloc(size);
      if (d->longest_abort_info == NULL)
        d->longest_abort_info_time = 0;   /* out of memory! */
      else
        {
          if (stm_decode_abort_info(d, elapsed_time, num,
                        (struct tx_abort_info *)d->longest_abort_info) != size)
            stm_fatalerror("during stm abort: object mutated unexpectedly\n");

          d->longest_abort_info_time = elapsed_time;
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

  AbortPrivateFromProtected(d);
  gcptrlist_clear(&d->list_of_read_objects);
  g2l_clear(&d->public_to_private);

  /* 'old_thread_local_obj' contains the old value from stm_thread_local_obj,
     but only when the transaction can be aborted; when it is inevitable
     old_thread_local_obj will be reset to NULL. */
  assert(d->thread_local_obj_ref = &stm_thread_local_obj);
  stm_thread_local_obj = d->old_thread_local_obj;
  d->old_thread_local_obj = NULL;

  // notifies the CPU that we're potentially in a spin loop
  SpinLoop(SPLP_ABORT);

  /* make the transaction no longer active */
  *d->active_ref = 0;
  d->atomic = 0;

  /* release the lock */
  spinlock_release(d->public_descriptor->collection_lock);

  /* clear memory registered by stm_clear_on_abort */
  if (d->mem_clear_on_abort)
    memset(d->mem_clear_on_abort, 0, d->mem_bytes_to_clear_on_abort);

  /* invoke the callbacks registered by stm_call_on_abort */
  stm_invoke_callbacks_on_abort(d);
  stm_clear_callbacks_on_abort(d);

  /* XXX */
  fprintf(stderr, "[%lx] abort %s\n",
          (long)d->public_descriptor_index, abort_names[num]);
  dprintf(("\n"
          "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
          "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
          "!!!!!!!!!!!!!!!!!!!!!  [%lx] abort %s\n"
          "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
          "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n"
          "\n", (long)d->public_descriptor_index, abort_names[num]));
  if (num != ABRT_MANUAL && d->max_aborts >= 0 && !d->max_aborts--)
    stm_fatalerror("unexpected abort!\n");

  // jump back to the setjmp_buf (this call does not return)
  stm_stop_sharedlock();
  if (d->longjmp_callback != NULL)
    {
      stm_begin_transaction(d->setjmp_buf, d->longjmp_callback);
      d->longjmp_callback(d->setjmp_buf);
    }
  else
    longjmp(*(jmp_buf *)d->setjmp_buf, 1);

  stm_fatalerror("longjmp() call should not return");
}

void AbortTransactionAfterCollect(struct tx_descriptor *d, int reason)
{
  if (*d->active_ref >= 0)
    {
      dprintf(("abort %d after collect!\n", reason));
      assert(*d->active_ref == 1);   /* not 2, which means inevitable */
      *d->active_ref = -reason;
    }
  assert(*d->active_ref < 0);
}

void AbortNowIfDelayed(void)
{
  struct tx_descriptor *d = thread_descriptor;
  if (*d->active_ref < 0)
    {
      int reason = -*d->active_ref;
      *d->active_ref = 1;
      AbortTransaction(reason);
    }
}

/************************************************************/

static void update_reads_size_limit(struct tx_descriptor *d)
{
  /* 'reads_size_limit' is set to ULONG_MAX if we are atomic; else
     we copy the value from reads_size_limit_nonatomic. */
  d->reads_size_limit = d->atomic ? ULONG_MAX : d->reads_size_limit_nonatomic;
}

long stm_atomic(long delta)
{
  struct tx_descriptor *d = thread_descriptor;
  if (delta) // no atomic-checks
    dprintf(("stm_atomic(%lu)\n", delta));
  d->atomic += delta;
  assert(d->atomic >= 0);
  update_reads_size_limit(d);
  return d->atomic;
}

static void init_transaction(struct tx_descriptor *d, int already_locked)
{
  assert(d->atomic == 0);
  assert(*d->active_ref == 0);
  if (!already_locked)
    stm_start_sharedlock();
  assert(*d->active_ref == 0);

  if (clock_gettime(CLOCK_MONOTONIC, &d->start_real_time) < 0) {
    d->start_real_time.tv_nsec = -1;
  }
  assert(d->list_of_read_objects.size == 0);
  assert(d->private_from_protected.size == 0);
  assert(d->num_private_from_protected_known_old == 0);
  assert(d->num_read_objects_known_old == 0);
  assert(!g2l_any_entry(&d->public_to_private));
  assert(d->old_thread_local_obj == NULL);

  d->count_reads = 1;
  fxcache_clear(&d->recent_reads_cache);
  gcptrlist_clear(&d->abortinfo);
}

void stm_begin_transaction(void *buf, void (*longjmp_callback)(void *))
{
  struct tx_descriptor *d = thread_descriptor;
  init_transaction(d, 0);
  *d->active_ref = 1;
  d->setjmp_buf = buf;
  d->longjmp_callback = longjmp_callback;
  d->old_thread_local_obj = stm_thread_local_obj;
  d->start_time = GetGlobalCurTime(d);
  update_reads_size_limit(d);
}

static void AcquireLocks(struct tx_descriptor *d)
{
  revision_t my_lock = d->my_lock;
  wlog_t *item;

  dprintf(("acquire_locks\n"));
  assert(!stm_has_got_any_lock(d));
  assert(d->public_descriptor->stolen_objects.size == 0);

  if (!g2l_any_entry(&d->public_to_private))
    return;

  G2L_LOOP_FORWARD(d->public_to_private, item)
    {
      gcptr R = item->addr;
      revision_t v;
    retry:
      assert(R->h_tid & GCFLAG_PUBLIC);
      assert(R->h_tid & GCFLAG_PUBLIC_TO_PRIVATE);
      v = ACCESS_ONCE(R->h_revision);
      if (IS_POINTER(v))     /* "has a more recent revision" */
        {
          assert(v != 0);
          AbortTransaction(ABRT_COMMIT);
        }
      if (v >= LOCKED)         // already locked by someone else
        {
          // we can always spinloop here: deadlocks should be impossible,
          // because G2L_LOOP_FORWARD should ensure a consistent ordering
          // of the R's.
          assert(v != my_lock);
          SpinLoop(SPLP_LOCKED_COMMIT);
          goto retry;
        }
      if (!bool_cas(&R->h_revision, v, my_lock))
        goto retry;

      gcptr L = item->val;
      assert(L->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED ?
             L->h_revision == (revision_t)R :
             L->h_revision == stm_private_rev_num);
      assert(v != stm_private_rev_num);
      assert(v & 1);
      L->h_revision = v;   /* store temporarily this value here */

    } G2L_LOOP_END;
}

static void CancelLocks(struct tx_descriptor *d)
{
  wlog_t *item;
  dprintf(("cancel_locks\n"));
  if (!g2l_any_entry(&d->public_to_private))
    return;

  G2L_LOOP_FORWARD(d->public_to_private, item)
    {
      gcptr R = item->addr;
      gcptr L = item->val;
      if (L == NULL)
        continue;

      revision_t expected, v = L->h_revision;

      if (L->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED)
        expected = (revision_t)R;
      else
        expected = stm_private_rev_num;

      if (v == expected)
        {
          assert(R->h_revision != d->my_lock);
          break;    /* done */
        }

      L->h_revision = expected;

#ifdef DUMP_EXTRA
      dprintf(("%p->h_revision = %p (CancelLocks)\n", R, (gcptr)v));
#endif
      assert(R->h_revision == d->my_lock);
      ACCESS_ONCE(R->h_revision) = v;

    } G2L_LOOP_END;
}

_Bool stm_has_got_any_lock(struct tx_descriptor *d)
{
  wlog_t *item;
  int found_locked, found_unlocked;

  if (!g2l_any_entry(&d->public_to_private))
    return 0;

  found_locked = 0;
  found_unlocked = 0;

  G2L_LOOP_FORWARD(d->public_to_private, item)
    {
      gcptr R = item->addr;
      gcptr L = item->val;
      if (L == NULL)
        continue;

      revision_t expected, v = L->h_revision;

      if (L->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED)
        expected = (revision_t)R;
      else
        expected = *d->private_revision_ref;

      if (v == expected)
        {
          assert(R->h_revision != d->my_lock);
          found_unlocked = 1;
          continue;
        }

      found_locked = 1;
      assert(found_unlocked == 0);  /* an unlocked followed by a locked: no */

    } G2L_LOOP_END;

  return found_locked;
}

static pthread_mutex_t mutex_prebuilt_gcroots = PTHREAD_MUTEX_INITIALIZER;

static void UpdateChainHeads(struct tx_descriptor *d, revision_t cur_time,
                             revision_t localrev)
{
  wlog_t *item;
  revision_t new_revision = cur_time + 1;     // make an odd number
  assert(new_revision & 1);

  if (!g2l_any_entry(&d->public_to_private))
    return;

  G2L_LOOP_FORWARD(d->public_to_private, item)
    {
      gcptr L = item->val;
      assert(!(L->h_tid & GCFLAG_VISITED));
      assert(!(L->h_tid & GCFLAG_PUBLIC_TO_PRIVATE));
      assert(!(L->h_tid & GCFLAG_PREBUILT_ORIGINAL));
      assert(!(L->h_tid & GCFLAG_MOVED));
      assert(L->h_revision != localrev);   /* modified by AcquireLocks() */

#ifdef DUMP_EXTRA
      dprintf(("%p->h_revision = %p (UpdateChainHeads)\n",
               L, (gcptr)new_revision));
#endif
      L->h_revision = new_revision;

      gcptr stub = stm_stub_malloc(d->public_descriptor, 0);
      stub->h_tid = (L->h_tid & STM_USER_TID_MASK) | GCFLAG_PUBLIC
                                                   | GCFLAG_STUB
                                                   | GCFLAG_SMALLSTUB
                                                   | GCFLAG_OLD;
      dprintf(("et.c: stm_stub_malloc -> %p\n", stub));
      stub->h_revision = ((revision_t)L) | 2;

      assert(!(L->h_tid & GCFLAG_HAS_ID));
      if (L->h_original) {
        stub->h_original = L->h_original;
      }
      else if (L->h_tid & GCFLAG_OLD) {
        stub->h_original = (revision_t)L;
      }
      else {
        /* There shouldn't be a public, young object without
           a h_original. They only come from stealing which
           always sets h_original */
        assert(0);
        /* L->h_original = (revision_t)stub; */
        /* if (L->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED) { */
        /*   ((gcptr)L->h_revision)->h_original = (revision_t)stub; */
        /* } */
      }
      
      item->val = stub;

    } G2L_LOOP_END;

  smp_wmb(); /* a memory barrier: make sure the new L->h_revisions are visible
                from other threads before we change the R->h_revisions */

  G2L_LOOP_FORWARD(d->public_to_private, item)
    {
      gcptr R = item->addr;
      revision_t v = (revision_t)item->val;

      assert(R->h_tid & GCFLAG_PUBLIC);
      assert(R->h_tid & GCFLAG_PUBLIC_TO_PRIVATE);
      assert(!(R->h_tid & GCFLAG_MOVED));
      assert(R->h_revision != localrev);

#ifdef DUMP_EXTRA
      dprintf(("%p->h_revision = %p (stub to %p)\n",
               R, (gcptr)v, (gcptr)item->val->h_revision));
#endif
      ACCESS_ONCE(R->h_revision) = v;

      if (R->h_tid & GCFLAG_PREBUILT_ORIGINAL)
        {
          /* cannot possibly get here more than once for a given value of R */
          pthread_mutex_lock(&mutex_prebuilt_gcroots);
          gcptrlist_insert(&stm_prebuilt_gcroots, R);
          pthread_mutex_unlock(&mutex_prebuilt_gcroots);
        }

    } G2L_LOOP_END;

  g2l_clear(&d->public_to_private);
}

void CommitPrivateFromProtected(struct tx_descriptor *d, revision_t cur_time)
{
  long i, size = d->private_from_protected.size;
  gcptr *items = d->private_from_protected.items;
  revision_t new_revision = cur_time + 1;     // make an odd number
  assert(new_revision & 1);
  assert(d->public_descriptor->stolen_objects.size == 0);

  for (i = 0; i < size; i++)
    {
      gcptr P = items[i];
      assert(P->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED);
      P->h_tid &= ~GCFLAG_PRIVATE_FROM_PROTECTED;

      if (!IS_POINTER(P->h_revision))
        {
          /* This case occurs when a GCFLAG_PRIVATE_FROM_PROTECTED object
             is stolen: it ends up as a value in 'public_to_private'.
             Its h_revision is then mangled by AcquireLocks(). */
          assert(P->h_revision != stm_private_rev_num);
          continue;
        }

      gcptr B = (gcptr)P->h_revision;
      P->h_revision = new_revision;

      if (B->h_tid & GCFLAG_PUBLIC)
        {
          assert(!(P->h_tid & GCFLAG_HAS_ID));

          /* B was stolen */
          while (1)
            {
              revision_t v = ACCESS_ONCE(B->h_revision);
              if (IS_POINTER(v))    /* "was modified" */
                AbortTransaction(ABRT_STOLEN_MODIFIED);

              if (bool_cas(&B->h_revision, v, (revision_t)P))
                break;
            }
        }      
      else
        {
          stmgcpage_free(B);
          dprintf(("commit: free backup at %p\n", B));
        }
    };
  gcptrlist_clear(&d->private_from_protected);
  d->num_private_from_protected_known_old = 0;
  d->num_read_objects_known_old = 0;
  dprintf(("private_from_protected: clear (commit)\n"));
}

void AbortPrivateFromProtected(struct tx_descriptor *d)
{
  long i, size = d->private_from_protected.size;
  gcptr *items = d->private_from_protected.items;

  for (i = 0; i < size; i++)
    {
      gcptr P = items[i];
      assert(P->h_tid & GCFLAG_PRIVATE_FROM_PROTECTED);
      assert(IS_POINTER(P->h_revision));
      P->h_tid &= ~GCFLAG_PRIVATE_FROM_PROTECTED;

      gcptr B = (gcptr)P->h_revision;
      assert(B->h_tid & GCFLAG_OLD);

      if (B->h_tid & GCFLAG_PUBLIC)
        {
          assert(!(B->h_tid & GCFLAG_BACKUP_COPY));
          P->h_tid |= GCFLAG_PUBLIC;
          assert(!(P->h_tid & GCFLAG_HAS_ID));
          if (!(P->h_tid & GCFLAG_OLD)) P->h_tid |= GCFLAG_MOVED;
          /* P becomes a public outdated object.  It may create an
             exception documented in doc-objects.txt: a public but young
             object.  It's still fine because it should only be seen by
             other threads during stealing, and as it's outdated,
             stealing will follow its h_revision (to B).
          */
        }
      else
        {
          /* copy the backup copy B back over the now-protected object P,
             and then free B, which will not be used any more. */
          size_t size = stmgc_size(B);
          assert(B->h_tid & GCFLAG_BACKUP_COPY);
          /* if h_original was 0, it must stay that way and not point
             to itself. (B->h_original may point to P) */
          revision_t h_original = P->h_original;
          memcpy(((char *)P) + offsetof(struct stm_object_s, h_revision),
                 ((char *)B) + offsetof(struct stm_object_s, h_revision),
                 size - offsetof(struct stm_object_s, h_revision));
          P->h_original = h_original;
          assert(!(P->h_tid & GCFLAG_BACKUP_COPY));
          stmgcpage_free(B);
          dprintf(("abort: free backup at %p\n", B));
        }
    };
  gcptrlist_clear(&d->private_from_protected);
  d->num_private_from_protected_known_old = 0;
  d->num_read_objects_known_old = 0;
  dprintf(("private_from_protected: clear (abort)\n"));
}

void CommitTransaction(int stay_inevitable)
{   /* must save roots around this call */
  revision_t cur_time;
  struct tx_descriptor *d = thread_descriptor;
  assert(*d->active_ref >= 1);
  assert(d->atomic == 0);
  dprintf(("CommitTransaction(%d): %p\n", stay_inevitable, d));

  spinlock_acquire(d->public_descriptor->collection_lock, 'C');  /*committing*/
  if (d->public_descriptor->stolen_objects.size != 0)
    stm_normalize_stolen_objects(d);
  AcquireLocks(d);

  if (is_inevitable(d))
    {
      // no-one else can have changed global_cur_time if I'm inevitable
      cur_time = d->start_time;
      if (!bool_cas(&global_cur_time, cur_time + 1, cur_time + 2))
        {
          stm_fatalerror("global_cur_time modified even though we are inev\n");
        }

      if (!stay_inevitable) {
        /* we simply don't release the mutex. */
        inev_mutex_release();
      }
    }
  else
    {
      while (1)
        {
          cur_time = ACCESS_ONCE(global_cur_time);
          if (cur_time & 1)
            {                    // there is another inevitable transaction
              CancelLocks(d);
              spinlock_release(d->public_descriptor->collection_lock);
              inev_mutex_acquire(d);   // wait until released
              inev_mutex_release();
              spinlock_acquire(d->public_descriptor->collection_lock, 'C');
              if (d->public_descriptor->stolen_objects.size != 0)
                stm_normalize_stolen_objects(d);

              AcquireLocks(d);
              continue;
            }
          if (bool_cas(&global_cur_time, cur_time, cur_time + 2))
            break;
        }
      // validate (but skip validation if nobody else committed)
      if (cur_time != d->start_time)
        if (!ValidateDuringTransaction(d, 1))
          AbortTransaction(ABRT_VALIDATE_COMMIT);
    }

  CommitPrivateFromProtected(d, cur_time);

  /* we cannot abort any more from here */
  d->setjmp_buf = NULL;
  d->old_thread_local_obj = NULL;
  gcptrlist_clear(&d->list_of_read_objects);

  dprintf(("\n"
          "*************************************\n"
          "**************************************  committed %ld\n"
          "*************************************\n",
           (long)cur_time));

  revision_t localrev = stm_private_rev_num;
  //UpdateProtectedChainHeads(d, cur_time, localrev);
  //smp_wmb();

  revision_t newrev = -(cur_time + 1);
  assert(newrev & 1);
  ACCESS_ONCE(stm_private_rev_num) = newrev;
  dprintf(("%p: stm_local_revision = %ld\n", d, (long)newrev));
  assert(d->private_revision_ref == &stm_private_rev_num);
  assert(d->read_barrier_cache_ref == &stm_read_barrier_cache);

  UpdateChainHeads(d, cur_time, localrev);

  spinlock_release(d->public_descriptor->collection_lock);
  d->num_commits++;
  *d->active_ref = 0;
  if (!stay_inevitable)
    stm_stop_sharedlock();

  /* clear the list of callbacks that would have been called
     on abort */
  stm_clear_callbacks_on_abort(d);
}

/************************************************************/

static void make_inevitable(struct tx_descriptor *d)
{
  d->setjmp_buf = NULL;
  d->old_thread_local_obj = NULL;
  *d->active_ref = 2;
  d->reads_size_limit_nonatomic = 0;
  update_reads_size_limit(d);
  dprintf(("make_inevitable(%p)\n", d));
}

static revision_t acquire_inev_mutex_and_mark_global_cur_time(
                      struct tx_descriptor *d)
{   /* must save roots around this call */
  revision_t cur_time;

  inev_mutex_acquire(d);
  while (1)
    {
      cur_time = ACCESS_ONCE(global_cur_time);
      assert((cur_time & 1) == 0);
      if (bool_cas(&global_cur_time, cur_time, cur_time + 1))
        break;
      /* else try again */
    }
  return cur_time;
}

void BecomeInevitable(const char *why)
{   /* must save roots around this call */
  revision_t cur_time;
  struct tx_descriptor *d = thread_descriptor;
  if (d == NULL || *d->active_ref != 1)
    return;  /* I am already inevitable, or not in a transaction at all
                (XXX statically we should know when we're outside
                a transaction) */

  /* XXX */
  /* fprintf(stderr, "[%lx] inevitable: %s\n", */
  /*          (long)d->public_descriptor_index, why); */
  dprintf(("[%lx] inevitable: %s\n",
           (long)d->public_descriptor_index, why));

  cur_time = acquire_inev_mutex_and_mark_global_cur_time(d);
  if (d->start_time != cur_time)
    {
      d->start_time = cur_time;
      if (!ValidateDuringTransaction(d, 0))
        {
          global_cur_time = cur_time;   // revert from (cur_time + 1)
          inev_mutex_release();
          AbortTransaction(ABRT_VALIDATE_INEV);
        }
    }
  make_inevitable(d);    /* cannot abort any more */
}

void BeginInevitableTransaction(int already_inevitable)
{   /* must save roots around this call */
  struct tx_descriptor *d = thread_descriptor;
  revision_t cur_time;

  init_transaction(d, already_inevitable);
  
  if (already_inevitable) {
    cur_time = ACCESS_ONCE(global_cur_time);
    assert((cur_time & 1) == 0);
    if (!bool_cas(&global_cur_time, cur_time, cur_time + 1)) {
      stm_fatalerror("there was a commit between a partial inevitable "
                     "commit and the continuation of the transaction\n");
    }
  }
  else {
    cur_time = acquire_inev_mutex_and_mark_global_cur_time(d);
  }

  d->start_time = cur_time;
  make_inevitable(d);
}

/************************************************************/

#if 0
static _Bool _PtrEq_Globals(gcptr G1, gcptr G2)
{
  /* This is a mess, because G1 and G2 can be different pointers to "the
     same" object, and it's hard to determine that.  Description of the
     idealized problem: we have chained lists following the 'h_revision'
     field from G1 and from G2, and we must return True if the chained
     lists end in the same object G and False if they don't.

     It's possible that G1 != G2 but G1->h_revision == G2->h_revision.
     More complicated cases are also possible.  This occurs because of
     random updates done in LatestGlobalRevision().  Note also that
     other threads can do concurrent updates.

     For now we simply use LatestGlobalRevision() and abort the current
     transaction if we see a too recent object.
  */
  struct tx_descriptor *d = thread_descriptor;
  if (G1->h_tid & GCFLAG_POSSIBLY_OUTDATED)
    G1 = LatestGlobalRevision(d, G1);
  if (G2->h_tid & GCFLAG_POSSIBLY_OUTDATED)
    G2 = LatestGlobalRevision(d, G2);
  return G1 == G2;
}

static _Bool _PtrEq_GlobalLocalCopy(gcptr G, gcptr L)
{
  struct tx_descriptor *d = thread_descriptor;
  wlog_t *entry;
  gcptr R;

  if (G->h_tid & GCFLAG_POSSIBLY_OUTDATED)
    R = LatestGlobalRevision(d, G);
  else
    R = G;

  G2L_FIND(d->global_to_local, R, entry, return 0);
  return L == entry->val;
}

_Bool stm_PtrEq(gcptr P1, gcptr P2)
{
  if (P1 == P2)
    return 1;
  else if (P1 == NULL || P2 == NULL)   /* and not P1 == P2 == NULL */
    return 0;

  if (P1->h_revision != stm_local_revision)
    {
      if (P2->h_revision != stm_local_revision)
        {
          /* P1 and P2 are two globals */
          return _PtrEq_Globals(P1, P2);
        }
      else if (P2->h_tid & GCFLAG_LOCAL_COPY)
        {
          /* P1 is a global, P2 is a local copy */
          return _PtrEq_GlobalLocalCopy(P1, P2);
        }
      else
        return 0;   /* P1 is global, P2 is new */
    }
  /* P1 is local, i.e. either new or a local copy */
  if (P2->h_revision != stm_local_revision)
    {
      if (P1->h_tid & GCFLAG_LOCAL_COPY)
        {
          /* P2 is a global, P1 is a local copy */
          return _PtrEq_GlobalLocalCopy(P2, P1);
        }
      else
        return 0;   /* P1 is new, P2 is global */
    }
  /* P1 and P2 are both locals (and P1 != P2) */
  return 0;
}
#endif
_Bool stm_PtrEq(gcptr P1, gcptr P2)
{
  abort();//XXX
}

/************************************************************/

struct tx_descriptor *stm_tx_head = NULL;
struct tx_public_descriptor *stm_descriptor_array[MAX_THREADS] = {0};
static revision_t descriptor_array_free_list = 0;

void _stm_test_forget_previous_state(void)
{
  /* debug: reset all global states, between tests */
  dprintf(("=======================================================\n"));
  assert(thread_descriptor == NULL);
  memset(stm_descriptor_array, 0, sizeof(stm_descriptor_array));
  descriptor_array_free_list = 0;
  stm_tx_head = NULL;
  stmgcpage_count(2);  /* reset */
}

struct tx_public_descriptor *stm_get_free_public_descriptor(revision_t *pindex)
{
  if (*pindex < 0)
    *pindex = descriptor_array_free_list;

  struct tx_public_descriptor *pd = stm_descriptor_array[*pindex];
  if (pd != NULL)
    {
      *pindex = pd->free_list_next;
      assert(*pindex >= 0);
    }
  return pd;
}

__thread gcptr stm_thread_local_obj;

void DescriptorInit(void)
{
  if (GCFLAG_PREBUILT != PREBUILT_FLAGS)
    {
      stm_fatalerror("fix PREBUILT_FLAGS in stmgc.h by giving "
                     "it the same value as GCFLAG_PREBUILT!\n");
    }
  else
    {
      revision_t i;
      struct tx_descriptor *d = stm_malloc(sizeof(struct tx_descriptor));
      memset(d, 0, sizeof(struct tx_descriptor));

      struct tx_public_descriptor *pd;
      i = descriptor_array_free_list;
      pd = stm_descriptor_array[i];
      if (pd != NULL) {
          /* we are reusing 'pd' */
          descriptor_array_free_list = pd->free_list_next;
          assert(descriptor_array_free_list >= 0);
          assert(pd->stolen_objects.size == 0);
          assert(pd->stolen_young_stubs.size == 0);
          /* there may be a thread holding the collection lock
             because it steals a stub belonging to the thread
             that previously owned this descriptor.
          */
      }
      else {
          /* no item in the free list */
          descriptor_array_free_list = i + 1;
          if (descriptor_array_free_list == MAX_THREADS) {
              stm_fatalerror("error: too many threads at the same time "
                             "in this process");
          }
          pd = stm_malloc(sizeof(struct tx_public_descriptor));
          memset(pd, 0, sizeof(struct tx_public_descriptor));
          stm_descriptor_array[i] = pd;
      }
      pd->free_list_next = -1;

      d->public_descriptor = pd;
      d->public_descriptor_index = i;
      d->my_lock = LOCKED + 2 * i;
      assert(d->my_lock & 1);
      assert(d->my_lock >= LOCKED);
      stm_private_rev_num = -d->my_lock;
      d->active_ref = &stm_active;
      d->nursery_current_ref = &stm_nursery_current;
      d->nursery_nextlimit_ref = &stm_nursery_nextlimit;
      d->private_revision_ref = &stm_private_rev_num;
      d->read_barrier_cache_ref = &stm_read_barrier_cache;
      stm_thread_local_obj = NULL;
      d->thread_local_obj_ref = &stm_thread_local_obj;
      d->max_aborts = -1;
      d->tcolor = dprintfcolor();
      d->pthreadid = pthread_self();
      d->tx_prev = NULL;
      d->tx_next = stm_tx_head;
      if (d->tx_next != NULL) d->tx_next->tx_prev = d;
      stm_tx_head = d;
      assert(thread_descriptor == NULL);
      thread_descriptor = d;

      dprintf(("[%lx] pthread %lx starting\n",
               (long)d->public_descriptor_index, (long)pthread_self()));

      stmgcpage_init_tls();
    }
}

void DescriptorDone(void)
{
    revision_t i;
    struct tx_descriptor *d = thread_descriptor;
    assert(d != NULL);
    assert(*d->active_ref == 0);

    /* our nursery is empty at this point.  The list 'stolen_objects'
       should have been emptied at the previous minor collection and
       should remain empty because we don't have any young object. */
    assert(d->public_descriptor->stolen_objects.size == 0);
    assert(d->public_descriptor->stolen_young_stubs.size == 0);
    gcptrlist_delete(&d->public_descriptor->stolen_objects);
    gcptrlist_delete(&d->public_descriptor->stolen_young_stubs);

    stmgcpage_done_tls();
    i = d->public_descriptor_index;
    assert(stm_descriptor_array[i] == d->public_descriptor);
    d->public_descriptor->free_list_next = descriptor_array_free_list;
    descriptor_array_free_list = i;
    if (d->tx_prev != NULL) d->tx_prev->tx_next = d->tx_next;
    if (d->tx_next != NULL) d->tx_next->tx_prev = d->tx_prev;
    if (d == stm_tx_head) stm_tx_head = d->tx_next;

    thread_descriptor = NULL;

    stm_thread_local_obj = (gcptr)0xBB;   /* to detect misuses */

    g2l_delete(&d->public_to_private);
    assert(d->private_from_protected.size == 0);
    gcptrlist_delete(&d->private_from_protected);
    gcptrlist_delete(&d->list_of_read_objects);
    gcptrlist_delete(&d->abortinfo);
    free(d->longest_abort_info);

    int num_aborts = 0, num_spinloops = 0;
    char line[256], *p = line;

    for (i=0; i<ABORT_REASONS; i++)
        num_aborts += d->num_aborts[i];
    for (i=0; i<SPINLOOP_REASONS; i++)
        num_spinloops += d->num_spinloops[i];

    p += sprintf(p, "[%lx] finishing: %d commits, %d aborts ",
                 (long)d->public_descriptor_index,
                 d->num_commits,
                 num_aborts);

    for (i=0; i<ABORT_REASONS; i++)
        p += sprintf(p, "%c%d", i == 0 ? '[' : ',',
                     d->num_aborts[i]);

    for (i=1; i<SPINLOOP_REASONS; i++)  /* num_spinloops[0] == num_aborts */
        p += sprintf(p, "%c%d", i == 1 ? '|' : ',',
                     d->num_spinloops[i]);

    p += sprintf(p, "]\n");
    dprintf(("%s", line));

    stm_free(d);
}
