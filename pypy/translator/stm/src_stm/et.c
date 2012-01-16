/* -*- c-basic-offset: 2 -*- */

#ifndef PYPY_NOT_MAIN_FILE

/* XXX assumes that time never wraps around (in a 'long'), which may be
 * correct on 64-bit machines but not on 32-bit machines if the process
 * runs for long enough.
 *
 * XXX measure the overhead of the global_timestamp
 */

#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
#include <string.h>

#define USE_PTHREAD_MUTEX    /* optional */
#ifdef USE_PTHREAD_MUTEX
# include <pthread.h>
#endif

#include "src_stm/et.h"
#include "src_stm/atomic_ops.h"

#ifdef PYPY_STANDALONE         /* obscure: cannot include debug_print.h if compiled */
# define RPY_STM_DEBUG_PRINT   /* via ll2ctypes; only include it in normal builds */
# include "src/debug_print.h"
#endif

/************************************************************/

#define IS_LOCKED(num)  ((num) < 0)
#define IS_LOCKED_OR_NEWER(num, max_age) \
    (((unsigned long)(num)) > ((unsigned long)(max_age)))
typedef long owner_version_t;

typedef struct {
  owner_version_t v;   // the current version number
} orec_t;

/*** Specify the number of orecs in the global array. */
#define NUM_STRIPES  1048576

/*** declare the table of orecs */
static char orecs[NUM_STRIPES * sizeof(orec_t)];

/*** map addresses to orec table entries */
inline static volatile orec_t* get_orec(void* addr)
{
  unsigned long index = (unsigned long)addr;
#ifdef RPY_STM_ASSERT
  assert(!(index & (sizeof(orec_t)-1)));
#endif
  char *p = orecs + (index & ((NUM_STRIPES-1) * sizeof(orec_t)));
  return (volatile orec_t *)p;
}

#include "src_stm/lists.c"

/************************************************************/

/* Uncomment the line to try this extra code.  Doesn't work reliably so far */
/*#define COMMIT_OTHER_INEV*/

#define ABORT_REASONS 8
#define SPINLOOP_REASONS 10
#define OTHERINEV_REASONS 5

struct tx_descriptor {
  jmp_buf *setjmp_buf;
  owner_version_t start_time;
  owner_version_t end_time;
  unsigned long last_known_global_timestamp;
  struct OrecList reads;
  unsigned num_commits;
  unsigned num_aborts[ABORT_REASONS];
  unsigned num_spinloops[SPINLOOP_REASONS];
#ifdef COMMIT_OTHER_INEV
  unsigned num_otherinev[OTHERINEV_REASONS];
#endif
  unsigned int spinloop_counter;
  owner_version_t my_lock_word;
  unsigned init_counter;
  struct RedoLog redolog;   /* last item, because it's the biggest one */
#ifdef RPY_STM_ASSERT
  int transaction_active;
#endif
};

/* global_timestamp contains in its lowest bit a flag equal to 1
   if there is an inevitable transaction running */
static volatile unsigned long global_timestamp = 2;
static __thread struct tx_descriptor *thread_descriptor = NULL;
#ifdef COMMIT_OTHER_INEV
static struct tx_descriptor *volatile thread_descriptor_inev;
static volatile unsigned long d_inev_checking = 0;
#endif

/************************************************************/

static unsigned long get_global_timestamp(struct tx_descriptor *d)
{
  return (d->last_known_global_timestamp = global_timestamp);
}

static _Bool change_global_timestamp(struct tx_descriptor *d,
                                     unsigned long old,
                                     unsigned long new)
{
  if (bool_cas(&global_timestamp, old, new))
    {
      d->last_known_global_timestamp = new;
      return 1;
    }
  return 0;
}

static void set_global_timestamp(struct tx_descriptor *d, unsigned long new)
{
  global_timestamp = new;
  d->last_known_global_timestamp = new;
}

static void tx_abort(int);

static void tx_spinloop(int num)
{
  unsigned int c;
  int i;
  struct tx_descriptor *d = thread_descriptor;
  d->num_spinloops[num]++;

  //printf("tx_spinloop(%d)\n", num);
  
  c = d->spinloop_counter;
  d->spinloop_counter = c * 9;
  i = c & 0xff0000;
  while (i >= 0) {
    spinloop();
    i -= 0x10000;
  }
}

static _Bool is_inevitable_or_inactive(struct tx_descriptor *d)
{
  return d->setjmp_buf == NULL;
}

static _Bool is_inevitable(struct tx_descriptor *d)
{
#ifdef RPY_STM_ASSERT
  assert(d->transaction_active);
#endif
  return is_inevitable_or_inactive(d);
}

/*** run the redo log to commit a transaction, and release the locks */
static void tx_redo(struct tx_descriptor *d)
{
  owner_version_t newver = d->end_time;
  wlog_t *item;
  /* loop in "forward" order: in this order, if there are duplicate orecs
     then only the last one has p != -1. */
  REDOLOG_LOOP_FORWARD(d->redolog, item)
    {
      *item->addr = item->val;
      /* but we must only unlock the orec if it's the last time it
         appears in the redolog list.  If it's not, then p == -1. */
      if (item->p != -1)
        {
          volatile orec_t* o = get_orec(item->addr);
          CFENCE;
          o->v = newver;
        }
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
          o->v = item->p;
        }
    } REDOLOG_LOOP_END;
}

/*** release locks and restore the old version number, ready to retry later */
static void releaseLocksForRetry(struct tx_descriptor *d)
{
  wlog_t *item;
  REDOLOG_LOOP_FORWARD(d->redolog, item)
    {
      if (item->p != -1)
        {
          volatile orec_t* o = get_orec(item->addr);
          o->v = item->p;
          item->p = -1;
        }
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
      ovt = o->v;

      // if orec not locked, lock it
      //
      // NB: if ovt > start time, we may introduce inconsistent
      // reads.  Since most writes are also reads, we'll just abort under this
      // condition.  This can introduce false conflicts
      if (!IS_LOCKED_OR_NEWER(ovt, d->start_time)) {
        if (!bool_cas(&o->v, ovt, d->my_lock_word))
          goto retry;
        // save old version to item->p.  Now we hold the lock.
        // in case of duplicate orecs, only the last one has p != -1.
        item->p = ovt;
      }
      // else if the location is too recent...
      else if (!IS_LOCKED(ovt))
        tx_abort(0);
      // else it is locked: if we don't hold the lock...
      else if (ovt != d->my_lock_word) {
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
#ifdef RPY_STM_ASSERT
  assert(d->transaction_active);
  d->transaction_active = 0;
#endif
  d->setjmp_buf = NULL;
}

static void tx_cleanup(struct tx_descriptor *d)
{
  // release the locks and restore version numbers
  releaseAndRevertLocks(d);
  // reset all lists
  common_cleanup(d);
}

static void tx_restart(struct tx_descriptor *d)
{
  jmp_buf *env = d->setjmp_buf;
  tx_cleanup(d);
  tx_spinloop(0);
  longjmp(*env, 1);
}

/*** increase the abort count and restart the transaction */
static void tx_abort(int reason)
{
  struct tx_descriptor *d = thread_descriptor;
  assert(!is_inevitable(d));
  d->num_aborts[reason]++;
#ifdef RPY_STM_DEBUG_PRINT
  PYPY_DEBUG_START("stm-abort");
  if (PYPY_HAVE_DEBUG_PRINTS) fprintf(PYPY_DEBUG_FILE, "thread %lx aborting\n",
                                      (long)pthread_self());
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
  assert(!is_inevitable(d));
  for (i=0; i<d->reads.size; i++)
    {
    retry:
      ovt = d->reads.items[i]->v;
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
  assert(!is_inevitable(d));
  for (i=0; i<d->reads.size; i++)
    {
      ovt = d->reads.items[i]->v;      // read this orec
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
static pthread_mutex_t mutex_inevitable = PTHREAD_MUTEX_INITIALIZER;
# ifdef RPY_STM_ASSERT
unsigned long locked_by = 0;
void mutex_lock(void)
{
  unsigned long pself = (unsigned long)pthread_self();
  if (PYPY_HAVE_DEBUG_PRINTS) fprintf(PYPY_DEBUG_FILE,
                                      "%lx: mutex inev locking...\n", pself);
  assert(locked_by != pself);
  pthread_mutex_lock(&mutex_inevitable);
  locked_by = pself;
  if (PYPY_HAVE_DEBUG_PRINTS) fprintf(PYPY_DEBUG_FILE,
                                      "%lx: mutex inev locked\n", pself);
}
void mutex_unlock(void)
{
  unsigned long pself = (unsigned long)pthread_self();
  locked_by = 0;
  if (PYPY_HAVE_DEBUG_PRINTS) fprintf(PYPY_DEBUG_FILE,
                                      "%lx: mutex inev unlocked\n", pself);
  pthread_mutex_unlock(&mutex_inevitable);
}
# else
#  define mutex_lock()    pthread_mutex_lock(&mutex_inevitable)
#  define mutex_unlock()  pthread_mutex_unlock(&mutex_inevitable)
# endif
#else
# define mutex_lock()     /* nothing */
# define mutex_unlock()   /* nothing */
#endif

#ifdef COMMIT_OTHER_INEV
unsigned long can_commit_with_other_inevitable(struct tx_descriptor *d,
                                               unsigned long expected)
{
  int i;
  owner_version_t ovt;
  unsigned long result = 0;
  struct tx_descriptor *d_inev;

  // 'd_inev_checking' is 1 or 2 when an inevitable transaction is running
  // and didn't start committing yet; otherwise it is 0.  It is normally 1
  // except in this function.
  if (!bool_cas(&d_inev_checking, 1, 2))
    {
      d->num_otherinev[4]++;
      return 0;
    }

  // optimization only: did the inevitable thread 'd_inev' read any data
  // that we are about to commit?  If we are sure that the answer is
  // negative, then commit anyway, because it cannot make the inevitable
  // thread fail.  We can safely check an approximation of this, because
  // we hold a lock on all orecs that we would like to write.  So if all
  // orecs read by d_inev are not locked now, then no conflict.  This
  // function is allowed to "fail" and give up rather than spinloop
  // waiting for a condition to be true, which is potentially dangerous
  // here, because we acquired all the locks.

  // Note that if the inevitable thread itself adds in parallel an extra
  // orec to d_inev->reads, *and* if this new orec is locked, then we
  // will miss it here; but the d_inev thread will spinloop waiting for
  // us to be done.  So even if we commit, the d_inev thread will just
  // wait and load the new committed value.

  // while we are in this function, the d_inev thread is prevented from
  // going too far with the commitTransaction() code because d_inev_checking
  // is greater than 1; it will just tx_spinloop(9).  (And of course it
  // cannot abort.)

  d_inev = thread_descriptor_inev;
  if (!bool_cas(&d_inev->reads.locked, 0, 1))
    {
      d->num_otherinev[1]++;
      goto give_up_1;
    }

  for (i=d_inev->reads.size; i--; )
    {
      ovt = d_inev->reads.items[i]->v;     // read this orec
      if (ovt == d->my_lock_word)
        {
          d->num_otherinev[2]++;
          goto give_up_2;
        }
    }
  assert(expected & 1);
  if (!change_global_timestamp(d, expected, expected + 2))
    {
      d->num_otherinev[3]++;
      goto give_up_2;
    }

  /* success: scale d_inet forward */
  d->num_otherinev[0]++;
  result = expected + 1;
  assert(d_inev->start_time == result - 2);
  d_inev->start_time = result;
  CFENCE;

 give_up_2:
  d_inev->reads.locked = 0;

 give_up_1:
  d_inev_checking = 1;
  return result;
}
#endif

void wait_end_inevitability(struct tx_descriptor *d)
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

void commitInevitableTransaction(struct tx_descriptor *d)
{
  unsigned long ts;
  _Bool ok;

#ifdef COMMIT_OTHER_INEV
  // reset d_inev_checking back from 1 to 0
  while (!bool_cas(&d_inev_checking, 1, 0))
    tx_spinloop(9);
#endif
  // no-one else can modify global_timestamp if I'm inevitable
  // and d_inev_checking is 0
  ts = get_global_timestamp(d);
  assert(ts & 1);
  set_global_timestamp(d, ts + 1);
  d->end_time = ts + 1;
  assert(d->end_time == (d->start_time + 2));

  // run the redo log, and release the locks
  tx_redo(d);

  mutex_unlock();
}

/* lazy/lazy read instrumentation */
long stm_read_word(long* addr)
{
  struct tx_descriptor *d = thread_descriptor;
  if (!d)
    return *addr;
#ifdef RPY_STM_ASSERT
  assert(d->transaction_active);
#endif

  // check writeset first
  wlog_t* found;
  REDOLOG_FIND(d->redolog, addr, found, goto not_found);
  return found->val;

 not_found:;
  // get the orec addr
  volatile orec_t* o = get_orec((void*)addr);
  owner_version_t ovt;

#ifdef COMMIT_OTHER_INEV
  // log orec BEFORE we spinloop waiting for the orec lock to be released,
  // for can_commit_with_other_inevitable()
  oreclist_insert(&d->reads, (orec_t*)o);
#endif

 retry:
  // read the orec BEFORE we read anything else
  ovt = o->v;
  CFENCE;

  // this tx doesn't hold any locks, so if the lock for this addr is held,
  // there is contention.  A lock is never hold for too long, so spinloop
  // until it is released.
  if (IS_LOCKED_OR_NEWER(ovt, d->start_time))
    {
      if (IS_LOCKED(ovt)) {
        tx_spinloop(7);
        goto retry;
      }
      // else this location is too new, scale forward
      owner_version_t newts = get_global_timestamp(d) & ~1;
#ifdef COMMIT_OTHER_INEV
      d->reads.size--;   // ignore the newly logged orec
#endif
      validate_fast(d, 1);
#ifdef COMMIT_OTHER_INEV
      d->reads.size++;
#endif
      d->start_time = newts;
    }

  // orec is unlocked, with ts <= start_time.  read the location
  long tmp = *addr;

  // postvalidate AFTER reading addr:
  CFENCE;
  if (o->v != ovt)
    goto retry;       /* oups, try again */

#ifndef COMMIT_OTHER_INEV
  oreclist_insert(&d->reads, (orec_t*)o);
#endif

  return tmp;
}

void stm_write_word(long* addr, long val)
{
  struct tx_descriptor *d = thread_descriptor;
  if (!d)
    {
      *addr = val;
      return;
    }
#ifdef RPY_STM_ASSERT
  assert(d->transaction_active);
#endif
  redolog_insert(&d->redolog, addr, val);
}


void stm_descriptor_init(void)
{
  if (thread_descriptor != NULL)
    thread_descriptor->init_counter++;
  else
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
      d->spinloop_counter = (unsigned int)(d->my_lock_word | 1);
      d->init_counter = 1;

      thread_descriptor = d;

#ifdef RPY_STM_DEBUG_PRINT
      if (PYPY_HAVE_DEBUG_PRINTS) fprintf(PYPY_DEBUG_FILE, "thread %lx starting\n",
                                          (long)pthread_self());
      PYPY_DEBUG_STOP("stm-init");
#endif
    }
}

void stm_descriptor_done(void)
{
  struct tx_descriptor *d = thread_descriptor;
  d->init_counter--;
  if (d->init_counter > 0)
    return;

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

#ifdef COMMIT_OTHER_INEV
    for (i=0; i<OTHERINEV_REASONS; i++)
      p += sprintf(p, "%c%d", i == 0 ? '|' : ',',
                   d->num_otherinev[i]);
#endif

    p += sprintf(p, "]\n");
    fwrite(line, 1, p - line, PYPY_DEBUG_FILE);
  }
  PYPY_DEBUG_STOP("stm-done");
#endif

  free(d);
}

void* stm_perform_transaction(void*(*callback)(void*), void *arg)
{
  void *result;
#ifdef RPY_STM_ASSERT
  /* you need to call descriptor_init() before calling stm_perform_transaction */
  assert(thread_descriptor != NULL);
#endif
  STM_begin_transaction();
  result = callback(arg);
  stm_commit_transaction();
  return result;
}

void stm_begin_transaction(jmp_buf* buf)
{
  struct tx_descriptor *d = thread_descriptor;
#ifdef RPY_STM_ASSERT
  assert(!d->transaction_active);
  d->transaction_active = 1;
#endif
  d->setjmp_buf = buf;
  d->start_time = d->last_known_global_timestamp & ~1;
}

long stm_commit_transaction(void)
{
  struct tx_descriptor *d = thread_descriptor;

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
      return d->start_time;
    }

  // bring that variable over to this CPU core (optimization, maybe)
  global_timestamp;

  // acquire locks
  acquireLocks(d);

  if (is_inevitable(d))
    {
      commitInevitableTransaction(d);
    }
  else
    {
      while (1)
        {
          unsigned long expected = get_global_timestamp(d);
          if (expected & 1)
            {
#ifdef COMMIT_OTHER_INEV
              // there is another inevitable transaction running.
              expected = can_commit_with_other_inevitable(d, expected);
              if (expected != 0)
                {
                  d->end_time = expected;
                  break;
                }
#endif
              // wait until it is done.  hopefully we can then proceed
              // without conflicts.
              wait_end_inevitability(d);
              continue;
            }
          if (change_global_timestamp(d, expected, expected + 2))
            {
              d->end_time = expected + 2;
              break;
            }
        }

      // validate (but skip validation if nobody else committed)
      if (d->end_time != (d->start_time + 2))
        validate(d);

      // run the redo log, and release the locks
      tx_redo(d);
    }

  // remember that this was a commit
  d->num_commits++;

  // reset all lists
  common_cleanup(d);
  return d->end_time;
}

void stm_try_inevitable(STM_CCHARP1(why))
{
  /* when a transaction is inevitable, its start_time is equal to
     global_timestamp and global_timestamp cannot be incremented
     by another thread.  We set the lowest bit in global_timestamp
     to 1. */
  struct tx_descriptor *d = thread_descriptor;

#ifdef RPY_STM_ASSERT
  PYPY_DEBUG_START("stm-inevitable");
  if (PYPY_HAVE_DEBUG_PRINTS)
    {
      fprintf(PYPY_DEBUG_FILE, "%s%s\n", why,
              (!d->transaction_active) ? " (inactive)" :
              is_inevitable(d) ? " (already inevitable)" : "");
    }
#endif

  if (is_inevitable_or_inactive(d))
    {
#ifdef RPY_STM_ASSERT
      PYPY_DEBUG_STOP("stm-inevitable");
#endif
      return;  /* I am already inevitable, or not in a transaction at all */
    }

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
          mutex_unlock();
          tx_spinloop(6);
          continue;
        }
      if (change_global_timestamp(d, curtime, curtime + 1))
        break;
      mutex_unlock();
    }
  d->setjmp_buf = NULL;   /* inevitable from now on */
#ifdef COMMIT_OTHER_INEV
  thread_descriptor_inev = d;
  CFENCE;
  d_inev_checking = 1;
#endif
#ifdef RPY_STM_ASSERT
  PYPY_DEBUG_STOP("stm-inevitable");
#endif
}

void stm_try_inevitable_if(jmp_buf *buf  STM_CCHARP(why))
{
  struct tx_descriptor *d = thread_descriptor;
  if (d->setjmp_buf == buf)
    stm_try_inevitable(STM_EXPLAIN1(why));
}

void stm_begin_inevitable_transaction(void)
{
  struct tx_descriptor *d = thread_descriptor;
  unsigned long curtime;

#ifdef RPY_STM_ASSERT
  assert(!d->transaction_active);
#endif

 retry:
  mutex_lock();   /* possibly waiting here */

  while (1)
    {
      curtime = global_timestamp;
      if (curtime & 1)
        {
          mutex_unlock();
          tx_spinloop(5);
          goto retry;
        }
      if (bool_cas(&global_timestamp, curtime, curtime + 1))
        break;
    }
#ifdef RPY_STM_ASSERT
  assert(!d->transaction_active);
  d->transaction_active = 1;
#endif
  d->setjmp_buf = NULL;
  d->start_time = curtime;
#ifdef COMMIT_OTHER_INEV
  thread_descriptor_inev = d;
  CFENCE;
  d_inev_checking = 1;
#endif
}

void stm_abort_and_retry(void)
{
  tx_abort(7);     /* manual abort */
}

// XXX little-endian only!
unsigned long stm_read_partial_word(int fieldsize, char *addr)
{
  int misalignment = ((long)addr) & (sizeof(void*)-1);
  long *p = (long*)(addr - misalignment);
  unsigned long word = stm_read_word(p);
  return word >> (misalignment * 8);
}

// XXX little-endian only!
void stm_write_partial_word(int fieldsize, char *addr, unsigned long nval)
{
  int misalignment = ((long)addr) & (sizeof(void*)-1);
  long *p = (long*)(addr - misalignment);
  long val = nval << (misalignment * 8);
  long word = stm_read_word(p);
  long mask = ((1L << (fieldsize * 8)) - 1) << (misalignment * 8);
  val = (val & mask) | (word & ~mask);
  stm_write_word(p, val);
}

#if PYPY_LONG_BIT == 32
long long stm_read_doubleword(long *addr)
{
  /* 32-bit only */
  unsigned long res0 = (unsigned long)stm_read_word(addr);
  unsigned long res1 = (unsigned long)stm_read_word(addr + 1);
  return (((unsigned long long)res1) << 32) | res0;
}

void stm_write_doubleword(long *addr, long long val)
{
  /* 32-bit only */
  stm_write_word(addr, (long)val);
  stm_write_word(addr + 1, (long)(val >> 32));
}
#endif

double stm_read_double(long *addr)
{
  long long x;
  double dd;
#if PYPY_LONG_BIT == 32
  x = stm_read_doubleword(addr);   /* 32 bits */
#else
  x = stm_read_word(addr);         /* 64 bits */
#endif
  assert(sizeof(double) == 8 && sizeof(long long) == 8);
  memcpy(&dd, &x, 8);
  return dd;
}

void stm_write_double(long *addr, double val)
{
  long long ll;
  assert(sizeof(double) == 8 && sizeof(long long) == 8);
  memcpy(&ll, &val, 8);
#if PYPY_LONG_BIT == 32
  stm_write_doubleword(addr, ll);   /* 32 bits */
#else
  stm_write_word(addr, ll);         /* 64 bits */
#endif
}

float stm_read_float(long *addr)
{
  unsigned int x;
  float ff;
#if PYPY_LONG_BIT == 32
  x = stm_read_word(addr);         /* 32 bits */
#else
  if (((long)(char*)addr) & 7) {
    addr = (long *)(((char *)addr) - 4);
    x = (unsigned int)(stm_read_word(addr) >> 32);   /* 64 bits, unaligned */
  }
  else
    x = (unsigned int)stm_read_word(addr);           /* 64 bits, aligned */
#endif
  assert(sizeof(float) == 4 && sizeof(unsigned int) == 4);
  memcpy(&ff, &x, 4);
  return ff;
}

void stm_write_float(long *addr, float val)
{
  unsigned int ii;
  assert(sizeof(float) == 4 && sizeof(unsigned int) == 4);
  memcpy(&ii, &val, 4);
#if PYPY_LONG_BIT == 32
  stm_write_word(addr, ii);         /* 32 bits */
#else
  stm_write_partial_word(4, (char *)addr, ii);   /* 64 bits */
#endif
}

#endif  /* PYPY_NOT_MAIN_FILE */
