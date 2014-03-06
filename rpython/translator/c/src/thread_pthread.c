
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

#ifdef __llvm__
#  define HAS_ATOMIC_ADD
#endif

#ifdef __GNUC__
#  if __GNUC__ > 4 || (__GNUC__ == 4 && __GNUC_MINOR__ >= 1)
#    define HAS_ATOMIC_ADD
#  endif
#endif

#ifdef HAS_ATOMIC_ADD
#  define atomic_add __sync_fetch_and_add
#else
#  if defined(__amd64__)
#    define atomic_add(ptr, value)  asm volatile ("lock addq %0, %1"        \
                                 : : "ri"(value), "m"(*(ptr)) : "memory")
#  elif defined(__i386__)
#    define atomic_add(ptr, value)  asm volatile ("lock addl %0, %1"        \
                                 : : "ri"(value), "m"(*(ptr)) : "memory")
#  else
#    error "Please use gcc >= 4.1 or write a custom 'asm' for your CPU."
#  endif
#endif

#define ASSERT_STATUS(call)                             \
    if (call != 0) {                                    \
        fprintf(stderr, "Fatal error: " #call "\n");    \
        abort();                                        \
    }

static void _debug_print(const char *msg)
{
#if 0
    int col = (int)pthread_self();
    col = 31 + ((col / 8) % 8);
    fprintf(stderr, "\033[%dm%s\033[0m", col, msg);
#endif
}

static volatile long pending_acquires = -1;
static pthread_mutex_t mutex_gil;
static pthread_cond_t cond_gil;

static void assert_has_the_gil(void)
{
#ifdef RPY_ASSERT
    assert(pthread_mutex_trylock(&mutex_gil) != 0);
    assert(pending_acquires >= 0);
#endif
}

long RPyGilAllocate(void)
{
    int status, error = 0;
    _debug_print("RPyGilAllocate\n");
    pending_acquires = -1;

    status = pthread_mutex_init(&mutex_gil,
                                pthread_mutexattr_default);
    CHECK_STATUS("pthread_mutex_init[GIL]");

    status = pthread_cond_init(&cond_gil,
                               pthread_condattr_default);
    CHECK_STATUS("pthread_cond_init[GIL]");

    if (error == 0) {
        pending_acquires = 0;
        RPyGilAcquire();
    }
    return (error == 0);
}

long RPyGilYieldThread(void)
{
    /* can be called even before RPyGilAllocate(), but in this case,
       pending_acquires will be -1 */
#ifdef RPY_ASSERT
    if (pending_acquires >= 0)
        assert_has_the_gil();
#endif
    if (pending_acquires <= 0)
        return 0;
    atomic_add(&pending_acquires, 1L);
    _debug_print("{");
    ASSERT_STATUS(pthread_cond_signal(&cond_gil));
    ASSERT_STATUS(pthread_cond_wait(&cond_gil, &mutex_gil));
    _debug_print("}");
    atomic_add(&pending_acquires, -1L);
    assert_has_the_gil();
    return 1;
}

void RPyGilRelease(void)
{
    _debug_print("RPyGilRelease\n");
#ifdef RPY_ASSERT
    assert(pending_acquires >= 0);
#endif
    assert_has_the_gil();
    ASSERT_STATUS(pthread_mutex_unlock(&mutex_gil));
    ASSERT_STATUS(pthread_cond_signal(&cond_gil));
}

#ifdef RPY_FASTGIL_VARNAME
#include <time.h>

static inline void *atomic_xchg(void **ptr, void *value)
{
    void *result;
    asm volatile (
#if defined(__amd64__)
                  "xchgq %0, %1  /* automatically locked */"
#elif defined(__i386__)
                  "xchgl %0, %1  /* automatically locked */"
#else
#  error "RPY_FASTGIL_VARNAME: only for x86 right now"
#endif
                  : "r"(result) : "0"(value), "m"(*ptr) : "memory");
    return result;
}

static inline timespec_add(struct timespec *t, unsigned long long incr)
{
    unsigned long long nsec = t->tv_nsec + incr;
    if (nsec >= 1000000000) {
        t->tv_sec += (nsec / 1000000000);
        nsec %= 1000000000;
    }
    t->tv_nsec = (long)nsec;
}

static inline void _acquire_gil_or_wait_for_fastgil_to_be_nonzero(void)
{
    /* Support for the JIT, which generates calls to external C
       functions using the following very fast pattern:

       * the global variable 'RPY_FASTGIL_VARNAME' (a macro naming the
         real variable) contains normally 0

       * before doing an external C call, the generated assembler sets
         this global variable to an in-stack pointer to its
         ASM_FRAMEDATA_HEAD structure (for asmgcc) or to 1 (for
         shadowstack, when implemented)

       * afterwards, it uses an atomic instruction to get the current
         value stored in the variable and to replace it with zero

       * if the old value was still the ASM_FRAMEDATA_HEAD pointer of
         this thread, everything is fine

       * otherwise, someone else stole the GIL.  The assembler calls a
         helper.  This helper first needs to unlink this thread's
         ASM_FRAMEDATA_HEAD from the chained list where it was put by
         the stealing code.  If the old value was zero, it means that
         the stealing code was this function here.  In that case, the
         helper needs to call RPyGilAcquire() again.  If, on the other
         hand, the old value is another ASM_FRAMEDATA_HEAD from a
         different thread, it means we just stole the fast GIL from this
         other thread.  In that case we store that different
         ASM_FRAMEDATA_HEAD into the chained list and return immediately.

       This function is a balancing act inspired by CPython 2.7's
       threading.py for _Condition.wait() (not the PyPy version, which
       was modified).  We need to wait for the real GIL to be released,
       but also notice if the fast GIL contains 1.  We can't afford a
       pure busy loop, so we have to sleep; but if we just sleep until
       the real GIL is released, we won't ever see the fast GIL being 1.
       The scheme here sleeps very little at first, and longer as time
       goes on.  Eventually, the real GIL should be released, so there
       is no point in trying to bound the maximal length of the wait.
    */
    unsigned long long delay = 0;
    struct timespec t;

    while (1) {

        /* try to see if we can steal the fast GIL */
        void *fastgilvalue;
        fastgilvalue = atomic_xchg(&RPY_FASTGIL_VARNAME, NULL);
        if (fastgilvalue != NULL) {
            /* yes, succeeded.  We know that the other thread is before
               the return to JITted assembler from the C function call.
               The JITted assembler will definitely call RPyGilAcquire()
               then.  So we can just pretend that the GIL --- which is
               still acquired --- is ours now.  We only need to fix
               the asmgcc linked list.
            */
            struct pypy_ASM_FRAMEDATA_HEAD0 *new =
                (struct pypy_ASM_FRAMEDATA_HEAD0 *)fastgilvalue;
            struct pypy_ASM_FRAMEDATA_HEAD0 *root = &pypy_g_ASM_FRAMEDATA_HEAD;
            struct pypy_ASM_FRAMEDATA_HEAD0 *next = root->as_next;
            new->as_next = next;
            new->as_prev = root;
            root->as_next = new;
            next->as_prev = new;
            return;
        }

        /* sleep for a bit of time */
        if (delay == 0) {
            clock_gettime(CLOCK_REALTIME, &t);
            delay = 100000;    /* in ns; initial delay is 0.1 ms */
        }
        timespec_add(&t, delay);
        int error = pthread_mutex_timedlock(&mutex_gil, &t);

        if (error == ETIMEDOUT) {
            delay = (delay * 3) / 2;
            continue;
        }
        else {
            ASSERT_STATUS(error);
            /* succeeded in acquiring the real GIL */
            return;
        }
    }
}
#endif

void RPyGilAcquire(void)
{
    _debug_print("about to RPyGilAcquire...\n");
#ifdef RPY_ASSERT
    assert(pending_acquires >= 0);
#endif
    if (pthread_mutex_trylock(&mutex_gil) == 0) {
        assert_has_the_gil();
        _debug_print("got it without waiting\n");
        return;
    }
    atomic_add(&pending_acquires, 1L);
#ifdef RPY_FASTGIL_VARNAME
    _acquire_gil_or_wait_for_fastgil_to_be_nonzero();
#else
    ASSERT_STATUS(pthread_mutex_lock(&mutex_gil));
#endif
    atomic_add(&pending_acquires, -1L);
    assert_has_the_gil();
    _debug_print("RPyGilAcquire\n");
}
