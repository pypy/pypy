/* -*- c-basic-offset: 2 -*- */

/************************************************************/

#define ABORT_REASONS 8
#define SPINLOOP_REASONS 10

struct tx_descriptor {
  jmp_buf *setjmp_buf;
  owner_version_t start_time;
  /*unsigned long last_known_global_timestamp;*/
  owner_version_t my_lock_word;
  struct OrecList reads;
  long atomic;   /* 0 = not atomic, > 0 atomic */
  long reads_size_limit, reads_size_limit_nonatomic; /* see should_break_tr. */
  int active;    /* 0 = inactive, 1 = regular, 2 = inevitable */
  unsigned num_commits;
  unsigned num_aborts[ABORT_REASONS];
  unsigned num_spinloops[SPINLOOP_REASONS];
  /*unsigned int spinloop_counter;*/
  struct RedoLog redolog;   /* last item, because it's the biggest one */
};

/* global_timestamp contains in its lowest bit a flag equal to 1
   if there is an inevitable transaction running */
static volatile unsigned long global_timestamp = 2;
static __thread struct tx_descriptor *thread_descriptor = NULL;

/************************************************************/

#define GETVERSION(o)     ((owner_version_t)((o)->h_version))
#define GETVERSIONREF(o)  ((volatile owner_version_t *)(&(o)->h_version))
#define SETVERSION(o, v)  (o)->h_version = (void *)(v)
#define GETTID(o)         ((o)->h_tid)

static unsigned long get_global_timestamp(struct tx_descriptor *d)
{
  return (/*d->last_known_global_timestamp =*/ global_timestamp);
}

static _Bool change_global_timestamp(struct tx_descriptor *d,
                                     unsigned long old,
                                     unsigned long new)
{
  if (bool_cas(&global_timestamp, old, new))
    {
      /*d->last_known_global_timestamp = new;*/
      return 1;
    }
  return 0;
}

static void set_global_timestamp(struct tx_descriptor *d, unsigned long new)
{
  global_timestamp = new;
  /*d->last_known_global_timestamp = new;*/
}

static void tx_abort(int);

static void tx_spinloop(int num)
{
  unsigned int c;
  int i;
  struct tx_descriptor *d = thread_descriptor;
  assert(d->active);
  d->num_spinloops[num]++;

  //printf("tx_spinloop(%d)\n", num);

#if 0
  c = d->spinloop_counter;
  d->spinloop_counter = c * 9;
  i = c & 0xff0000;
  while (i >= 0) {
    spinloop();
    i -= 0x10000;
  }
#else
  spinloop();
#endif
}

static _Bool is_inevitable(struct tx_descriptor *d)
{
  /* Assert that we are running a transaction.
     Returns True if this transaction is inevitable. */
  assert(d->active == 1 + !d->setjmp_buf);
  return d->active == 2;
}

/*** run the redo log to commit a transaction, and release the locks.
     Cannot abort any more. */
static void tx_redo(struct tx_descriptor *d, owner_version_t newver)
{
  wlog_t *item;
  REDOLOG_LOOP_FORWARD(d->redolog, item)
    {
      void *globalobj = item->addr;
      void *localobj = item->val;
      long size = pypy_g__stm_getsize(localobj);
      memcpy(((char *)globalobj) + sizeof(orec_t),
             ((char *)localobj) + sizeof(orec_t),
             size - sizeof(orec_t));
      /* unlock the orec */
      volatile orec_t* o = get_orec(globalobj);
      CFENCE;
      SETVERSION(o, newver);
    } REDOLOG_LOOP_END;
}

/*** on abort, release locks and restore the old version number. */
static void releaseAndRevertLocks(struct tx_descriptor *d)
{
  wlog_t *item;
  REDOLOG_LOOP_FORWARD(d->redolog, item)
    {
      if (item->p != -1)
        {
          volatile orec_t* o = get_orec(item->addr);
          SETVERSION(o, item->p);
        }
    } REDOLOG_LOOP_END;
}

/*** release locks and restore the old version number, ready to retry later */
static void releaseLocksForRetry(struct tx_descriptor *d)
{
  wlog_t *item;
  REDOLOG_LOOP_FORWARD(d->redolog, item)
    {
      volatile orec_t* o = get_orec(item->addr);
      assert(item->p != -1);
      SETVERSION(o, item->p);
      item->p = -1;
    } REDOLOG_LOOP_END;
}

/*** lock all locations */
static void acquireLocks(struct tx_descriptor *d)
{
  wlog_t *item;
  // try to lock every location in the write set
  REDOLOG_LOOP_BACKWARD(d->redolog, item)
    {
      // get orec, read its version#
      volatile orec_t* o = get_orec(item->addr);
      owner_version_t ovt;

    retry:
      ovt = GETVERSION(o);

      // if orec not locked, lock it
      //
      // NB: if ovt > start time, we may introduce inconsistent
      // reads.  Since most writes are also reads, we'll just abort under this
      // condition.  This can introduce false conflicts
      if (!IS_LOCKED_OR_NEWER(ovt, d->start_time)) {
        if (!bool_cas(GETVERSIONREF(o), ovt, d->my_lock_word))
          goto retry;
        // save old version to item->p.  Now we hold the lock.
        item->p = ovt;
      }
      // else if the location is too recent...
      else if (!IS_LOCKED(ovt))
        tx_abort(0);
      // else it is locked: check it's not by me
      else {
        assert(ovt != d->my_lock_word);
        // we can either abort or spinloop.  Because we are at the end of
        // the transaction we might try to spinloop, even though after the
        // lock is released the ovt will be very recent, possibly
        // > d->start_time.  It is necessary to spinloop in case we are
        // inevitable, so use that as a criteria.  Another solution to avoid
        // deadlocks would be to sort the order in which we take the locks.
        if (is_inevitable(d))
          tx_spinloop(8);
        else
          tx_abort(6);
        goto retry;
      }
    } REDOLOG_LOOP_END;
}

static void common_cleanup(struct tx_descriptor *d)
{
  d->reads.size = 0;
  redolog_clear(&d->redolog);
  d->active = 0;
}

static void tx_restart(struct tx_descriptor *d)
{
  // release the locks and restore version numbers
  releaseAndRevertLocks(d);
  // notifies the CPU that we're potentially in a spin loop
  tx_spinloop(0);
  // reset all lists
  common_cleanup(d);
  // jump back to the setjmp_buf (this call does not return)
  longjmp(*d->setjmp_buf, 1);
}

/*** increase the abort count and restart the transaction */
static void tx_abort(int reason)
{
  struct tx_descriptor *d = thread_descriptor;
  assert(d->active == 1);
  d->num_aborts[reason]++;
#ifdef RPY_STM_DEBUG_PRINT
  PYPY_DEBUG_START("stm-abort");
  if (PYPY_HAVE_DEBUG_PRINTS)
      fprintf(PYPY_DEBUG_FILE, "thread %lx aborting %d\n",
                               (long)pthread_self(), reason);
  PYPY_DEBUG_STOP("stm-abort");
#endif
  tx_restart(d);
}

/**
 * fast-path validation, assuming that I don't hold locks.
 */
static void validate_fast(struct tx_descriptor *d, int lognum)
{
  int i;
  owner_version_t ovt;
  assert(d->active == 1);
  for (i=0; i<d->reads.size; i++)
    {
    retry:
      ovt = GETVERSION(d->reads.items[i]);
      if (IS_LOCKED_OR_NEWER(ovt, d->start_time))
        {
          // If locked, we wait until it becomes unlocked.  The chances are
          // that it will then have a very recent start_time, likely
          // > d->start_time, but it might still be better than always aborting
          if (IS_LOCKED(ovt))
            {
              tx_spinloop(lognum);  /* tx_spinloop(1), tx_spinloop(2),
                                       tx_spinloop(3) */
              goto retry;
            }
          else
            // abort if the timestamp is newer than my start time.  
            tx_abort(lognum);  /* tx_abort(1), tx_abort(2), tx_abort(3) */
        }
    }
}

/**
 * validate the read set by making sure that all orecs that we've read have
 * timestamps at least as old as our start time, unless we locked those orecs.
 */
static void validate(struct tx_descriptor *d)
{
  int i;
  owner_version_t ovt;
  assert(d->active == 1);
  for (i=0; i<d->reads.size; i++)
    {
      ovt = GETVERSION(d->reads.items[i]);      // read this orec
      if (IS_LOCKED_OR_NEWER(ovt, d->start_time))
        {
          if (!IS_LOCKED(ovt))
            // if unlocked and newer than start time, abort
            tx_abort(4);
          else
            {
              // if locked and not by me, abort
              if (ovt != d->my_lock_word)
                tx_abort(5);
            }
        }
    }
}

#ifdef USE_PTHREAD_MUTEX
/* mutex: only to avoid busy-looping too much in tx_spinloop() below */

# if defined(RPY_STM_ASSERT) && defined(PTHREAD_ERRORCHECK_MUTEX_INITIALIZER_NP)
static pthread_mutex_t mutex_inevitable = PTHREAD_ERRORCHECK_MUTEX_INITIALIZER_NP;
# else
static pthread_mutex_t mutex_inevitable = PTHREAD_MUTEX_INITIALIZER;
# endif

# ifndef RPY_STM_ASSERT
#  define mutex_lock()    pthread_mutex_lock(&mutex_inevitable)
#  define mutex_unlock()  pthread_mutex_unlock(&mutex_inevitable)
# else
static unsigned long locked_by = 0;
static void mutex_lock(void)
{
  unsigned long pself = (unsigned long)pthread_self();
#ifdef RPY_STM_DEBUG_PRINT
  //fprintf(stderr, "%lx: mutex inev locking...\n", pself);
#endif
  assert(locked_by != pself);
  pthread_mutex_lock(&mutex_inevitable);
  locked_by = pself;
#ifdef RPY_STM_DEBUG_PRINT
  //fprintf(stderr, "%lx: mutex inev locked\n", pself);
#endif
}
static void mutex_unlock(void)
{
  unsigned long pself = (unsigned long)pthread_self();
  assert(locked_by == pself);
  locked_by = 0;
#ifdef RPY_STM_DEBUG_PRINT
  //fprintf(stderr, "%lx: mutex inev unlocked\n", pself);
#endif
  pthread_mutex_unlock(&mutex_inevitable);
}
# endif
#else
# define mutex_lock()     /* nothing */
# define mutex_unlock()   /* nothing */
#endif

static void wait_end_inevitability(struct tx_descriptor *d)
{
  unsigned long curts;
  releaseLocksForRetry(d);

  // We are going to wait until the other inevitable transaction
  // finishes.  XXX We could do better here: we could check if
  // committing 'd' would create a conflict for the other inevitable
  // thread 'd_inev' or not.  It requires peeking in 'd_inev' from this
  // thread (which we never do so far) in order to do something like
  // 'validate_fast(d_inev); d_inev->start_time = updated;'

  while ((curts = get_global_timestamp(d)) & 1)
    {
      // while we're about to wait anyway, we can do a validate_fast
      if (d->start_time < curts - 1)
        {
          validate_fast(d, 3);
          d->start_time = curts - 1;
        }
      tx_spinloop(4);
      mutex_lock();
      mutex_unlock();
    }
  acquireLocks(d);
}

static owner_version_t commitInevitableTransaction(struct tx_descriptor *d)
{
  unsigned long ts;
  _Bool ok;

  // no-one else can modify global_timestamp if I'm inevitable
  // and d_inev_checking is 0
  ts = get_global_timestamp(d);
  assert(ts & 1);
  ts += 1;
  set_global_timestamp(d, ts);
  assert(ts == (d->start_time + 2));

  /* we still have the locks acquired, but we changed the global timestamp
   * and we can release the mutex here.  The locked orecs will be updated
   * immediately afterwards by tx_redo(). */
  mutex_unlock();

  return ts;
}

/* lazy/lazy read instrumentation */
#define STM_DO_READ(READ_OPERATION)                                     \
 retry:                                                                 \
  /* read the orec BEFORE we read anything else */                      \
  ovt = GETVERSION(o);                                                  \
  CFENCE;                                                               \
                                                                        \
  /* this tx doesn't hold any locks, so if the lock for this addr is */ \
  /* held, there is contention.  A lock is never hold for too long,  */ \
  /* so spinloop until it is released.                               */ \
  if (IS_LOCKED_OR_NEWER(ovt, d->start_time))                           \
    {                                                                   \
      if (IS_LOCKED(ovt)) {                                             \
        tx_spinloop(7);                                                 \
        goto retry;                                                     \
      }                                                                 \
      /* else this location is too new, scale forward */                \
      owner_version_t newts = get_global_timestamp(d) & ~1;             \
      validate_fast(d, 1);                                              \
      d->start_time = newts;                                            \
    }                                                                   \
                                                                        \
  /* orec is unlocked, with ts <= start_time.  read the location */     \
  READ_OPERATION;                                                       \
                                                                        \
  if (!is_inevitable(d)) {                                              \
    /* if is_inevitable(), then we don't need to do the checking of  */ \
    /* o->version done below --- but more importantly, we don't need */ \
    /* to insert o in the OrecList.  We *do* need to do the above    */ \
    /* check for locked-ness, though.                                */ \
                                                                        \
    /* postvalidate AFTER reading addr: */                              \
    CFENCE;                                                             \
    if (__builtin_expect(GETVERSION(o) != ovt, 0))                      \
      goto retry;       /* oups, try again */                           \
                                                                        \
    oreclist_insert(&d->reads, (orec_t*)o);                             \
  }


#define STM_READ_WORD(SIZE, SUFFIX, TYPE)                               \
TYPE stm_read_int##SIZE##SUFFIX(void* addr, long offset)                \
{                                                                       \
  struct tx_descriptor *d = thread_descriptor;                          \
  volatile orec_t *o = get_orec(addr);                                  \
  owner_version_t ovt;                                                  \
                                                                        \
  assert(sizeof(TYPE) == SIZE);                                         \
                                                                        \
  if ((GETTID(o) & GCFLAG_WAS_COPIED) != 0)                             \
    {                                                                   \
      /* Look up in the thread-local dictionary. */                     \
      wlog_t *found;                                                    \
      REDOLOG_FIND(d->redolog, addr, found, goto not_found);            \
      orec_t *localobj = (orec_t *)found->val;                          \
      assert((GETTID(localobj) & GCFLAG_GLOBAL) == 0);                  \
      return *(TYPE *)(((char *)localobj) + offset);                    \
                                                                        \
    not_found:;                                                         \
    }                                                                   \
                                                                        \
  TYPE tmp;                                                             \
  STM_DO_READ(tmp = *(TYPE *)(((char *)addr) + offset));                \
  return tmp;                                                           \
}

STM_READ_WORD(1, , char)
STM_READ_WORD(2, , short)
STM_READ_WORD(4, , int)
STM_READ_WORD(8, , long long)
STM_READ_WORD(8,f, double)
STM_READ_WORD(4,f, float)

void stm_copy_transactional_to_raw(void *src, void *dst, long size)
{
  struct tx_descriptor *d = thread_descriptor;
  volatile orec_t *o = get_orec(src);
  owner_version_t ovt;

  /* don't copy the header */
  src = ((char *)src) + sizeof(orec_t);
  dst = ((char *)dst) + sizeof(orec_t);
  size -= sizeof(orec_t);

  STM_DO_READ(memcpy(dst, src, size));
}

long stm_descriptor_init(void)
{
  if (thread_descriptor == NULL)
    {
      struct tx_descriptor *d = malloc(sizeof(struct tx_descriptor));
      memset(d, 0, sizeof(struct tx_descriptor));

#ifdef RPY_STM_DEBUG_PRINT
      PYPY_DEBUG_START("stm-init");
#endif

      /* initialize 'my_lock_word' to be a unique negative number */
      d->my_lock_word = (owner_version_t)d;
      if (!IS_LOCKED(d->my_lock_word))
        d->my_lock_word = ~d->my_lock_word;
      assert(IS_LOCKED(d->my_lock_word));

      thread_descriptor = d;

#ifdef RPY_STM_DEBUG_PRINT
      if (PYPY_HAVE_DEBUG_PRINTS)
        fprintf(PYPY_DEBUG_FILE, "thread %lx starting with id %lx\n",
                (long)pthread_self(), (long)d->my_lock_word);
      PYPY_DEBUG_STOP("stm-init");
#endif
      return 1;
    }
  else
    return 0;   /* already initialized */
}

void stm_descriptor_done(void)
{
  struct tx_descriptor *d = thread_descriptor;
  assert(d != NULL);
  assert(d->active == 0);

  thread_descriptor = NULL;

#ifdef RPY_STM_DEBUG_PRINT
  PYPY_DEBUG_START("stm-done");
  if (PYPY_HAVE_DEBUG_PRINTS) {
    int num_aborts = 0, num_spinloops = 0;
    int i, prevchar;
    char line[256], *p = line;

    for (i=0; i<ABORT_REASONS; i++)
      num_aborts += d->num_aborts[i];
    for (i=0; i<SPINLOOP_REASONS; i++)
      num_spinloops += d->num_spinloops[i];

    p += sprintf(p, "thread %lx: %d commits, %d aborts\n",
                 (long)pthread_self(),
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

static void update_reads_size_limit(struct tx_descriptor *d)
{
  /* 'reads_size_limit' is set to LONG_MAX if we are atomic; else
     we copy the value from reads_size_limit_nonatomic. */
  d->reads_size_limit = d->atomic ? LONG_MAX : d->reads_size_limit_nonatomic;
}

static void begin_transaction(jmp_buf* buf)
{
  struct tx_descriptor *d = thread_descriptor;
  assert(d->active == 0);
  d->active = 1;
  d->setjmp_buf = buf;
  d->start_time = (/*d->last_known_global_timestamp*/ global_timestamp) & ~1;
  update_reads_size_limit(d);
}

static void make_inevitable(struct tx_descriptor *d)
{
  d->setjmp_buf = NULL;
  d->active = 2;
  d->reads_size_limit_nonatomic = 0;
  update_reads_size_limit(d);
}

void stm_begin_inevitable_transaction(void)
{
  /* Equivalent to begin_transaction(); stm_try_inevitable();
     except more efficient */
  struct tx_descriptor *d = thread_descriptor;
  assert(d->active == 0);
  make_inevitable(d);

  mutex_lock();
  while (1)
    {
      unsigned long curtime = get_global_timestamp(d);
      if (!(curtime & 1) && change_global_timestamp(d, curtime, curtime + 1))
        {
          d->start_time = curtime;
          break;
        }
      tx_spinloop(6);
    }
}

void stm_commit_transaction(void)
{
  owner_version_t end_time;
  struct tx_descriptor *d = thread_descriptor;
  assert(d->active != 0);

  // if I don't have writes, I'm committed
  if (!redolog_any_entry(&d->redolog))
    {
      if (is_inevitable(d))
        {
          unsigned long ts = get_global_timestamp(d);
          assert(ts & 1);
          set_global_timestamp(d, ts - 1);
          mutex_unlock();
        }
      d->num_commits++;
      common_cleanup(d);
      return;
    }

  // bring that variable over to this CPU core (optimization, maybe)
  /* global_timestamp; */

  // acquire locks
  acquireLocks(d);

  if (is_inevitable(d))
    {
      end_time = commitInevitableTransaction(d);
    }
  else
    {
      while (1)
        {
          unsigned long expected = get_global_timestamp(d);
          if (expected & 1)
            {
              // wait until it is done.  hopefully we can then proceed
              // without conflicts.
              wait_end_inevitability(d);
              continue;
            }
          if (change_global_timestamp(d, expected, expected + 2))
            {
              end_time = expected + 2;
              break;
            }
        }

      // validate (but skip validation if nobody else committed)
      if (end_time != (d->start_time + 2))
        validate(d);
    }

  // run the redo log, and release the locks
  tx_redo(d, end_time);

  // remember that this was a commit
  d->num_commits++;

  // reset all lists
  common_cleanup(d);
}

void stm_try_inevitable(STM_CCHARP1(why))
{
  /* when a transaction is inevitable, its start_time is equal to
     global_timestamp and global_timestamp cannot be incremented
     by another thread.  We set the lowest bit in global_timestamp
     to 1. */
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

  while (1)
    {
      unsigned long curtime = get_global_timestamp(d);
      if (d->start_time != (curtime & ~1))
        {                             /* scale forward */
          validate_fast(d, 2);
          d->start_time = curtime & ~1;
        }
      mutex_lock();
      if (curtime & 1)   /* there is, or was, already an inevitable thread */
        {
          /* should we spinloop here, or abort (and likely come back
             in try_inevitable() very soon)?  unclear.  For now
             let's try to spinloop, after the waiting done by
             acquiring the mutex */
        }
      else
        {
          if (change_global_timestamp(d, curtime, curtime + 1))
            break;
        }
      mutex_unlock();
      tx_spinloop(6);
    }
  make_inevitable(d);   /* inevitable from now on */

#ifdef RPY_STM_DEBUG_PRINT
  PYPY_DEBUG_STOP("stm-inevitable");
#endif
}

void stm_abort_and_retry(void)
{
  tx_abort(7);     /* manual abort */
}

/************************************************************/

static __thread void *rpython_tls_object;

void stm_set_tls(void *newtls)
{
  rpython_tls_object = newtls;
}

void *stm_get_tls(void)
{
  return rpython_tls_object;
}

void stm_del_tls(void)
{
  rpython_tls_object = NULL;
}

void *stm_tldict_lookup(void *key)
{
  struct tx_descriptor *d = thread_descriptor;
  wlog_t* found;
  REDOLOG_FIND(d->redolog, key, found, goto not_found);
  return found->val;

 not_found:
  return NULL;
}

void stm_tldict_add(void *key, void *value)
{
  struct tx_descriptor *d = thread_descriptor;
  assert(d != NULL);
  redolog_insert(&d->redolog, key, value);
}

void stm_tldict_enum(void)
{
  struct tx_descriptor *d = thread_descriptor;
  wlog_t *item;
  void *tls = stm_get_tls();

  REDOLOG_LOOP_FORWARD(d->redolog, item)
    {
      pypy_g__stm_enum_callback(tls, item->addr, item->val);
    } REDOLOG_LOOP_END;
}

long stm_in_transaction(void)
{
  struct tx_descriptor *d = thread_descriptor;
  return d->active;
}

long stm_is_inevitable(void)
{
  struct tx_descriptor *d = thread_descriptor;
  return is_inevitable(d);
}

static long stm_regular_length_limit = LONG_MAX;

void stm_add_atomic(long delta)
{
  struct tx_descriptor *d = thread_descriptor;
  d->atomic += delta;
  update_reads_size_limit(d);
}

long stm_get_atomic(void)
{
  struct tx_descriptor *d = thread_descriptor;
  return d->atomic;
}

long stm_should_break_transaction(void)
{
  struct tx_descriptor *d = thread_descriptor;

  /* a single comparison to handle all cases:

     - if d->atomic, then we should return False.  This is done by
       forcing reads_size_limit to LONG_MAX as soon as atomic > 0.

     - otherwise, if is_inevitable(), then we should return True.
       This is done by forcing both reads_size_limit and
       reads_size_limit_nonatomic to 0 in that case.

     - finally, the default case: return True if d->reads.size is
       greater than reads_size_limit == reads_size_limit_nonatomic.
  */
#ifdef RPY_STM_ASSERT
  /* reads_size_limit is LONG_MAX if d->atomic, or else it is equal to
     reads_size_limit_nonatomic. */
  assert(d->reads_size_limit == (d->atomic ? LONG_MAX :
                                     d->reads_size_limit_nonatomic));
  /* if is_inevitable(), reads_size_limit_nonatomic should be 0
     (and thus reads_size_limit too, if !d->atomic.) */
  if (is_inevitable(d))
    assert(d->reads_size_limit_nonatomic == 0);
#endif

  return d->reads.size >= d->reads_size_limit;
}

void stm_set_transaction_length(long length_max)
{
  struct tx_descriptor *d = thread_descriptor;
  stm_try_inevitable(STM_EXPLAIN1("set_transaction_length"));
  stm_regular_length_limit = length_max;
}

#define END_MARKER   ((void*)-8)   /* keep in sync with stmframework.py */

void stm_perform_transaction(long(*callback)(void*, long), void *arg,
                             void *save_and_restore)
{
  jmp_buf _jmpbuf;
  long volatile v_counter = 0;
  void **volatile v_saved_value;
  long volatile v_atomic = thread_descriptor->atomic;
  assert((!thread_descriptor->active) == (!v_atomic));
  v_saved_value = *(void***)save_and_restore;
  /***/
  setjmp(_jmpbuf);
  /* After setjmp(), the local variables v_* are preserved because they
   * are volatile.  The other variables are only declared here. */
  struct tx_descriptor *d = thread_descriptor;
  long counter, result;
  void **restore_value;
  counter = v_counter;
  d->atomic = v_atomic;
  restore_value = v_saved_value;
  if (!d->atomic)
    {
      /* In non-atomic mode, we are now between two transactions.
         It means that in the next transaction's collections we know
         that we won't need to access the shadows stack beyond its
         current position.  So we add an end marker. */
      *restore_value++ = END_MARKER;
    }
  *(void***)save_and_restore = restore_value;

  do
    {
      v_counter = counter + 1;
      /* initialize 'reads_size_limit_nonatomic' from the configured
         length limit, scaled down by a factor of 2 for each time we
         retry an aborted transaction.  Note that as soon as such a
         shortened transaction succeeds, the next one will again have
         full length, for now. */
      d->reads_size_limit_nonatomic = stm_regular_length_limit >> counter;
      if (!d->atomic)
        begin_transaction(&_jmpbuf);

      /* invoke the callback in the new transaction */
      result = callback(arg, counter);

      v_atomic = d->atomic;
      if (!d->atomic)
        stm_commit_transaction();
      counter = 0;
    }
  while (result == 1);  /* also stops if we got an RPython exception */

  if (d->atomic && thread_descriptor->setjmp_buf == &_jmpbuf)
    stm_try_inevitable(STM_EXPLAIN1("perform_transaction left with atomic"));

  *(void***)save_and_restore = v_saved_value;
}

#undef GETVERSION
#undef GETVERSIONREF
#undef SETVERSION
#undef GETTID
