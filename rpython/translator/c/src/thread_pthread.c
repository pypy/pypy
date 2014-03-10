
/* Posix threads interface (from CPython) */

#include <unistd.h>   /* for the _POSIX_xxx and _POSIX_THREAD_xxx defines */
#include <stdlib.h>
#include <pthread.h>
#include <signal.h>
#include <stdio.h>
#include <errno.h>
#include <assert.h>
#include <sys/time.h>

/* The following is hopefully equivalent to what CPython does
   (which is trying to compile a snippet of code using it) */
#ifdef PTHREAD_SCOPE_SYSTEM
#  ifndef PTHREAD_SYSTEM_SCHED_SUPPORTED
#    define PTHREAD_SYSTEM_SCHED_SUPPORTED
#  endif
#endif

#if !defined(pthread_attr_default)
#  define pthread_attr_default ((pthread_attr_t *)NULL)
#endif
#if !defined(pthread_mutexattr_default)
#  define pthread_mutexattr_default ((pthread_mutexattr_t *)NULL)
#endif
#if !defined(pthread_condattr_default)
#  define pthread_condattr_default ((pthread_condattr_t *)NULL)
#endif

#define CHECK_STATUS(name)  if (status != 0) { perror(name); error = 1; }

/* The POSIX spec requires that use of pthread_attr_setstacksize
   be conditional on _POSIX_THREAD_ATTR_STACKSIZE being defined. */
#ifdef _POSIX_THREAD_ATTR_STACKSIZE
# ifndef THREAD_STACK_SIZE
#  define THREAD_STACK_SIZE   0   /* use default stack size */
# endif

# if (defined(__APPLE__) || defined(__FreeBSD__)) && defined(THREAD_STACK_SIZE) && THREAD_STACK_SIZE == 0
   /* The default stack size for new threads on OSX is small enough that
    * we'll get hard crashes instead of 'maximum recursion depth exceeded'
    * exceptions.
    *
    * The default stack size below is the minimal stack size where a
    * simple recursive function doesn't cause a hard crash.
    */
#  undef  THREAD_STACK_SIZE
#  define THREAD_STACK_SIZE       0x400000
# endif
/* for safety, ensure a viable minimum stacksize */
# define THREAD_STACK_MIN    0x8000  /* 32kB */
#else  /* !_POSIX_THREAD_ATTR_STACKSIZE */
# ifdef THREAD_STACK_SIZE
#  error "THREAD_STACK_SIZE defined but _POSIX_THREAD_ATTR_STACKSIZE undefined"
# endif
#endif

/* XXX This implementation is considered (to quote Tim Peters) "inherently
   hosed" because:
     - It does not guarantee the promise that a non-zero integer is returned.
     - The cast to long is inherently unsafe.
     - It is not clear that the 'volatile' (for AIX?) and ugly casting in the
       latter return statement (for Alpha OSF/1) are any longer necessary.
*/
long RPyThreadGetIdent(void)
{
	volatile pthread_t threadid;
	/* Jump through some hoops for Alpha OSF/1 */
	threadid = pthread_self();

#ifdef __CYGWIN__
	/* typedef __uint32_t pthread_t; */
	return (long) threadid;
#else
	if (sizeof(pthread_t) <= sizeof(long))
		return (long) threadid;
	else
		return (long) *(long *) &threadid;
#endif
}

static long _pypythread_stacksize = 0;

static void *bootstrap_pthread(void *func)
{
  ((void(*)(void))func)();
  return NULL;
}

long RPyThreadStart(void (*func)(void))
{
	pthread_t th;
	int status;
#if defined(THREAD_STACK_SIZE) || defined(PTHREAD_SYSTEM_SCHED_SUPPORTED)
	pthread_attr_t attrs;
#endif
#if defined(THREAD_STACK_SIZE)
	size_t tss;
#endif

#if defined(THREAD_STACK_SIZE) || defined(PTHREAD_SYSTEM_SCHED_SUPPORTED)
	pthread_attr_init(&attrs);
#endif
#ifdef THREAD_STACK_SIZE
	tss = (_pypythread_stacksize != 0) ? _pypythread_stacksize
		: THREAD_STACK_SIZE;
	if (tss != 0)
		pthread_attr_setstacksize(&attrs, tss);
#endif
#if defined(PTHREAD_SYSTEM_SCHED_SUPPORTED) && !defined(__FreeBSD__)
        pthread_attr_setscope(&attrs, PTHREAD_SCOPE_SYSTEM);
#endif

	status = pthread_create(&th, 
#if defined(THREAD_STACK_SIZE) || defined(PTHREAD_SYSTEM_SCHED_SUPPORTED)
				 &attrs,
#else
				 (pthread_attr_t*)NULL,
#endif
				 bootstrap_pthread,
				 (void *)func
				 );

#if defined(THREAD_STACK_SIZE) || defined(PTHREAD_SYSTEM_SCHED_SUPPORTED)
	pthread_attr_destroy(&attrs);
#endif
	if (status != 0)
            return -1;

        pthread_detach(th);

#ifdef __CYGWIN__
	/* typedef __uint32_t pthread_t; */
	return (long) th;
#else
	if (sizeof(pthread_t) <= sizeof(long))
		return (long) th;
	else
		return (long) *(long *) &th;
#endif
}

long RPyThreadGetStackSize(void)
{
	return _pypythread_stacksize;
}

long RPyThreadSetStackSize(long newsize)
{
#if defined(THREAD_STACK_SIZE)
	pthread_attr_t attrs;
	size_t tss_min;
	int rc;
#endif

	if (newsize == 0) {    /* set to default */
		_pypythread_stacksize = 0;
		return 0;
	}

#if defined(THREAD_STACK_SIZE)
# if defined(PTHREAD_STACK_MIN)
	tss_min = PTHREAD_STACK_MIN > THREAD_STACK_MIN ? PTHREAD_STACK_MIN
		: THREAD_STACK_MIN;
# else
	tss_min = THREAD_STACK_MIN;
# endif
	if (newsize >= tss_min) {
		/* validate stack size by setting thread attribute */
		if (pthread_attr_init(&attrs) == 0) {
			rc = pthread_attr_setstacksize(&attrs, newsize);
			pthread_attr_destroy(&attrs);
			if (rc == 0) {
				_pypythread_stacksize = newsize;
				return 0;
			}
		}
	}
	return -1;
#else
	return -2;
#endif
}

#ifdef GETTIMEOFDAY_NO_TZ
#define RPY_GETTIMEOFDAY(ptv) gettimeofday(ptv)
#else
#define RPY_GETTIMEOFDAY(ptv) gettimeofday(ptv, (struct timezone *)NULL)
#endif

#define RPY_MICROSECONDS_TO_TIMESPEC(microseconds, ts) \
do { \
    struct timeval tv; \
    RPY_GETTIMEOFDAY(&tv); \
    tv.tv_usec += microseconds % 1000000; \
    tv.tv_sec += microseconds / 1000000; \
    tv.tv_sec += tv.tv_usec / 1000000; \
    tv.tv_usec %= 1000000; \
    ts.tv_sec = tv.tv_sec; \
    ts.tv_nsec = tv.tv_usec * 1000; \
} while(0)

int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag)
{
    return RPyThreadAcquireLockTimed(lock, waitflag ? -1 : 0, /*intr_flag=*/0);
}

/************************************************************/
#ifdef USE_SEMAPHORES
/************************************************************/

#include <semaphore.h>

void RPyThreadAfterFork(void)
{
}

int RPyThreadLockInit(struct RPyOpaque_ThreadLock *lock)
{
	int status, error = 0;
	lock->initialized = 0;
	status = sem_init(&lock->sem, 0, 1);
	CHECK_STATUS("sem_init");
	if (error)
		return 0;
	lock->initialized = 1;
	return 1;
}

void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock)
{
	int status, error = 0;
	if (lock->initialized) {
		status = sem_destroy(&lock->sem);
		CHECK_STATUS("sem_destroy");
		/* 'error' is ignored;
		   CHECK_STATUS already printed an error message */
	}
}

/*
 * As of February 2002, Cygwin thread implementations mistakenly report error
 * codes in the return value of the sem_ calls (like the pthread_ functions).
 * Correct implementations return -1 and put the code in errno. This supports
 * either.
 */
static int
rpythread_fix_status(int status)
{
	return (status == -1) ? errno : status;
}

RPyLockStatus
RPyThreadAcquireLockTimed(struct RPyOpaque_ThreadLock *lock,
			  RPY_TIMEOUT_T microseconds, int intr_flag)
{
	RPyLockStatus success;
	sem_t *thelock = &lock->sem;
	int status, error = 0;
	struct timespec ts;

	if (microseconds > 0)
		RPY_MICROSECONDS_TO_TIMESPEC(microseconds, ts);
	do {
	    if (microseconds > 0)
		status = rpythread_fix_status(sem_timedwait(thelock, &ts));
	    else if (microseconds == 0)
		status = rpythread_fix_status(sem_trywait(thelock));
	    else
		status = rpythread_fix_status(sem_wait(thelock));
	    /* Retry if interrupted by a signal, unless the caller wants to be
	       notified.  */
	} while (!intr_flag && status == EINTR);

	/* Don't check the status if we're stopping because of an interrupt.  */
	if (!(intr_flag && status == EINTR)) {
	    if (microseconds > 0) {
		if (status != ETIMEDOUT)
		    CHECK_STATUS("sem_timedwait");
	    }
	    else if (microseconds == 0) {
		if (status != EAGAIN)
		    CHECK_STATUS("sem_trywait");
	    }
	    else {
		CHECK_STATUS("sem_wait");
	    }
	}

	if (status == 0) {
	    success = RPY_LOCK_ACQUIRED;
	} else if (intr_flag && status == EINTR) {
	    success = RPY_LOCK_INTR;
	} else {
	    success = RPY_LOCK_FAILURE;
	}
	return success;
}

void RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock)
{
	sem_t *thelock = &lock->sem;
	int status, error = 0;

	status = sem_post(thelock);
	CHECK_STATUS("sem_post");
}

/************************************************************/
#else                                      /* no semaphores */
/************************************************************/

struct RPyOpaque_ThreadLock *alllocks;   /* doubly-linked list */

void RPyThreadAfterFork(void)
{
	/* Mess.  We have no clue about how it works on CPython on OSX,
	   but the issue is that the state of mutexes is not really
	   preserved across a fork().  So we need to walk over all lock
	   objects here, and rebuild their mutex and condition variable.

	   See e.g. http://hackage.haskell.org/trac/ghc/ticket/1391 for
	   a similar bug about GHC.
	*/
	struct RPyOpaque_ThreadLock *p = alllocks;
	alllocks = NULL;
	while (p) {
		struct RPyOpaque_ThreadLock *next = p->next;
		int was_locked = p->locked;
		RPyThreadLockInit(p);
		p->locked = was_locked;
		p = next;
	}
}

int RPyThreadLockInit(struct RPyOpaque_ThreadLock *lock)
{
	int status, error = 0;

	lock->initialized = 0;
	lock->locked = 0;

	status = pthread_mutex_init(&lock->mut,
				    pthread_mutexattr_default);
	CHECK_STATUS("pthread_mutex_init");

	status = pthread_cond_init(&lock->lock_released,
				   pthread_condattr_default);
	CHECK_STATUS("pthread_cond_init");

	if (error)
		return 0;
	lock->initialized = 1;
	/* add 'lock' in the doubly-linked list */
	if (alllocks)
		alllocks->prev = lock;
	lock->next = alllocks;
	lock->prev = NULL;
	alllocks = lock;
	return 1;
}

void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock)
{
	int status, error = 0;
	if (lock->initialized) {
		/* remove 'lock' from the doubly-linked list */
		if (lock->prev)
			lock->prev->next = lock->next;
		else {
			assert(alllocks == lock);
			alllocks = lock->next;
		}
		if (lock->next)
			lock->next->prev = lock->prev;

		status = pthread_mutex_destroy(&lock->mut);
		CHECK_STATUS("pthread_mutex_destroy");

		status = pthread_cond_destroy(&lock->lock_released);
		CHECK_STATUS("pthread_cond_destroy");

		/* 'error' is ignored;
		   CHECK_STATUS already printed an error message */
	}
}

RPyLockStatus
RPyThreadAcquireLockTimed(struct RPyOpaque_ThreadLock *lock,
			  RPY_TIMEOUT_T microseconds, int intr_flag)
{
	RPyLockStatus success;
	int status, error = 0;

	status = pthread_mutex_lock( &lock->mut );
	CHECK_STATUS("pthread_mutex_lock[1]");

	if (lock->locked == 0) {
	    success = RPY_LOCK_ACQUIRED;
	} else if (microseconds == 0) {
	    success = RPY_LOCK_FAILURE;
	} else {
		struct timespec ts;
		if (microseconds > 0)
		    RPY_MICROSECONDS_TO_TIMESPEC(microseconds, ts);
		/* continue trying until we get the lock */

		/* mut must be locked by me -- part of the condition
		 * protocol */
		success = RPY_LOCK_FAILURE;
		while (success == RPY_LOCK_FAILURE) {
		    if (microseconds > 0) {
			status = pthread_cond_timedwait(
			    &lock->lock_released,
			    &lock->mut, &ts);
			if (status == ETIMEDOUT)
			    break;
			CHECK_STATUS("pthread_cond_timed_wait");
		    }
		    else {
			status = pthread_cond_wait(
			    &lock->lock_released,
			    &lock->mut);
			CHECK_STATUS("pthread_cond_wait");
		    }

		    if (intr_flag && status == 0 && lock->locked) {
			/* We were woken up, but didn't get the lock.  We probably received
			 * a signal.  Return RPY_LOCK_INTR to allow the caller to handle
			 * it and retry.  */
			success = RPY_LOCK_INTR;
			break;
		    } else if (status == 0 && !lock->locked) {
			success = RPY_LOCK_ACQUIRED;
		    } else {
			success = RPY_LOCK_FAILURE;
		    }
		}
	}
	if (success == RPY_LOCK_ACQUIRED) lock->locked = 1;
	status = pthread_mutex_unlock( &lock->mut );
	CHECK_STATUS("pthread_mutex_unlock[1]");

	if (error) success = RPY_LOCK_FAILURE;
	return success;
}

void RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock)
{
	int status, error = 0;

	status = pthread_mutex_lock( &lock->mut );
	CHECK_STATUS("pthread_mutex_lock[3]");

	lock->locked = 0;

	status = pthread_mutex_unlock( &lock->mut );
	CHECK_STATUS("pthread_mutex_unlock[3]");

	/* wake up someone (anyone, if any) waiting on the lock */
	status = pthread_cond_signal( &lock->lock_released );
	CHECK_STATUS("pthread_cond_signal");
}

/************************************************************/
#endif                                     /* no semaphores */
/************************************************************/


/************************************************************/
/* GIL code                                                 */
/************************************************************/


#include <time.h>


#define ASSERT_STATUS(call)                             \
    if (call != 0) {                                    \
        fprintf(stderr, "Fatal error: " #call "\n");    \
        abort();                                        \
    }

/* Idea:

   - "The GIL" is a composite concept.  "The GIL is locked" means
     that the global variable 'rpy_fastgil' is zero *and* the
     'mutex_gil' is acquired.  Conversely, "the GIL is unlocked" means
     that rpy_fastgil != 0 *or* mutex_gil is released.  It should never
     be the case that these two conditions are true at the same time.

   - Let's call "thread 1" the thread with the GIL.  Whenever it does an
     external function call, it sets 'rpy_fastgil' to a non-null value.
     This is the cheapest way to release the GIL.  When it returns from
     the function call, this thread attempts to atomically reset
     rpy_fastgil to zero.  In the common case where it works, thread 1
     has got the GIL back and so continues to run.

   - But "thread 2" is eagerly waiting for thread 1 to become blocked in
     some long-running call.  About every millisecond it checks if
     'rpy_fastgil' is non-null, by atomically resetting it to zero.
     If it was non-null, it means that the GIL was not actually locked,
     and thread 2 has now got the GIL.

   - If there are more threads, they are really sleeping, waiting on the
     'mutex_gil_stealer' held by thread 2.

   - An additional mechanism is used for when thread 1 wants to
     explicitly yield the GIL to thread 2: it does so by releasing
     'mutex_gil' (which is otherwise not released) but keeping the
     value of 'rpy_fastgil' to zero.
*/

void *rpy_fastgil = NULL;
static pthread_mutex_t mutex_gil_stealer;
static pthread_mutex_t mutex_gil;
static pthread_once_t mutex_gil_once = PTHREAD_ONCE_INIT;

static void init_mutex_gil(void)
{
    ASSERT_STATUS(pthread_mutex_init(&mutex_gil_stealer,
                                     pthread_mutexattr_default));
    ASSERT_STATUS(pthread_mutex_init(&mutex_gil, pthread_mutexattr_default));
    ASSERT_STATUS(pthread_mutex_lock(&mutex_gil));
}

static inline void prepare_mutexes(void)
{
    pthread_once(&mutex_gil_once, &init_mutex_gil);
}

static inline void *atomic_xchg(void **ptr, void *value)
{
    void *result;
#if defined(__amd64__)
    asm volatile ("xchgq %0, %2  /* automatically locked */"
                  : "=r"(result) : "0"(value), "m"(*ptr) : "memory");
#elif defined(__i386__)
    asm volatile ("xchgl %0, %2  /* automatically locked */"
                  : "=r"(result) : "0"(value), "m"(*ptr) : "memory");
#else
    /* requires gcc >= 4.1 */
    while (1) {
        result = *ptr;
        if (__sync_bool_compare_and_swap(ptr, result, value))
            break;
    }
#endif
    return result;
}

static inline void timespec_add(struct timespec *t, long incr)
{
    long nsec = t->tv_nsec + incr;
    if (nsec >= 1000000000) {
        t->tv_sec += 1;
        nsec -= 1000000000;
        assert(nsec < 1000000000);
    }
    t->tv_nsec = nsec;
}

void RPyGilAcquire(void)
{
    /* Acquires the GIL.  Note: this function saves and restores 'errno'.
     */
    void *old_fastgil = atomic_xchg(&rpy_fastgil, NULL);

    if (old_fastgil != NULL) {
        /* If we get a non-NULL value, it means that no other thread had the
           GIL, and the exchange was successful.  'mutex_gil' should still
           be locked at this point.
        */
    }
    else {
        /* Otherwise, another thread is busy with the GIL. */
        int old_errno = errno;

        /* Enter the waiting queue from the end.  Assuming a roughly
           first-in-first-out order, this will nicely give the threads
           a round-robin chance.
        */
        prepare_mutexes();
        ASSERT_STATUS(pthread_mutex_lock(&mutex_gil_stealer));

        /* We are now the stealer thread.  Steals! */
        while (1) {
            int delay = 1000000;   /* 1 ms... */
            struct timespec t;

            /* Sleep for one interval of time.  We may be woken up earlier
               if 'mutex_gil' is released.
            */
            clock_gettime(CLOCK_REALTIME, &t);
            timespec_add(&t, delay);
            int error_from_timedlock = pthread_mutex_timedlock(&mutex_gil, &t);

            if (error_from_timedlock != ETIMEDOUT) {
                ASSERT_STATUS(error_from_timedlock);

                /* We arrive here if 'mutex_gil' was recently released
                   and we just relocked it.
                 */
                assert(rpy_fastgil == NULL);
                old_fastgil = (void *)1;
                break;
            }

            /* Busy-looping here.  Try to look again if 'rpy_fastgil' is
               non-NULL.
            */
            if (rpy_fastgil != NULL) {
                old_fastgil = atomic_xchg(&rpy_fastgil, NULL);
                if (old_fastgil != NULL) {
                    /* yes, got a non-NULL value! */
                    break;
                }
            }
            /* Otherwise, loop back. */
        }

        errno = old_errno;
    }

#ifdef PYPY_USE_ASMGCC
    if (old_fastgil != (void *)1) {
        /* this case only occurs from the JIT compiler */
        struct pypy_ASM_FRAMEDATA_HEAD0 *new =
            (struct pypy_ASM_FRAMEDATA_HEAD0 *)old_fastgil;
        struct pypy_ASM_FRAMEDATA_HEAD0 *root = &pypy_g_ASM_FRAMEDATA_HEAD;
        struct pypy_ASM_FRAMEDATA_HEAD0 *next = root->as_next;
        new->as_next = next;
        new->as_prev = root;
        root->as_next = new;
        next->as_prev = new;
    }
#else
    assert(old_fastgil == (void *)1);
#endif
    return;
}

/*
void RPyGilRelease(void)
{
    Releases the GIL in order to do an external function call.
    We assume that the common case is that the function call is
    actually very short, and optimize accordingly.

    Note: this function is defined as a 'static inline' in thread.h.
}
*/

void RPyGilYieldThread(void)
{
    assert(rpy_fastgil == NULL);

    /* Explicitly release the 'mutex_gil'.
     */
    prepare_mutexes();
    ASSERT_STATUS(pthread_mutex_unlock(&mutex_gil));

    /* Now nobody has got the GIL, because 'mutex_gil' is released (but
       rpy_fastgil is still zero).  Call RPyGilAcquire().  It will
       enqueue ourselves at the end of the 'mutex_gil_stealer' queue.
       If there is no other waiting thread, it will fall through both
       its pthread_mutex_lock() and pthread_mutex_timedlock() now.
     */
    RPyGilAcquire();
}
