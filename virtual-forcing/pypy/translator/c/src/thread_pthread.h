
/* Posix threads interface (from CPython) */

#include <pthread.h>
#include <stdio.h>
#include <errno.h>

/* The POSIX spec says that implementations supporting the sem_*
   family of functions must indicate this by defining
   _POSIX_SEMAPHORES. */   
#ifdef _POSIX_SEMAPHORES
/* On FreeBSD 4.x, _POSIX_SEMAPHORES is defined empty, so 
   we need to add 0 to make it work there as well. */
#if (_POSIX_SEMAPHORES+0) == -1
#define HAVE_BROKEN_POSIX_SEMAPHORES
#else
#include <semaphore.h>
#endif
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

/* Whether or not to use semaphores directly rather than emulating them with
 * mutexes and condition variables:
 */
#if defined(_POSIX_SEMAPHORES) && !defined(HAVE_BROKEN_POSIX_SEMAPHORES)
#  define USE_SEMAPHORES
#else
#  undef USE_SEMAPHORES
#endif


#define CHECK_STATUS(name)  if (status != 0) { perror(name); error = 1; }

/********************* structs ***********/

#ifdef USE_SEMAPHORES

#include <semaphore.h>

struct RPyOpaque_ThreadLock {
	sem_t sem;
	int initialized;
};

#define RPyOpaque_INITEXPR_ThreadLock  { { /* sem */ }, 0 }

#else                                      /* no semaphores */

/* A pthread mutex isn't sufficient to model the Python lock type
   (see explanations in CPython's Python/thread_pthread.h */
struct RPyOpaque_ThreadLock {
	char             locked; /* 0=unlocked, 1=locked */
	char             initialized;
	/* a <cond, mutex> pair to handle an acquire of a locked lock */
	pthread_cond_t   lock_released;
	pthread_mutex_t  mut;
};

#define RPyOpaque_INITEXPR_ThreadLock  {        \
		0, 0,                           \
		PTHREAD_COND_INITIALIZER,       \
		PTHREAD_MUTEX_INITIALIZER       \
	}
#endif                                     /* no semaphores */

/* prototypes */

long RPyThreadGetIdent(void);
long RPyThreadStart(void (*func)(void));
int RPyThreadLockInit(struct RPyOpaque_ThreadLock *lock);
void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock);
int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag);
void RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock);
long RPyThreadGetStackSize(void);
long RPyThreadSetStackSize(long);


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

/* The POSIX spec requires that use of pthread_attr_setstacksize
   be conditional on _POSIX_THREAD_ATTR_STACKSIZE being defined. */
#ifdef _POSIX_THREAD_ATTR_STACKSIZE
# ifndef THREAD_STACK_SIZE
#  define THREAD_STACK_SIZE   0   /* use default stack size */
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
#if SIZEOF_PTHREAD_T <= SIZEOF_LONG
	return (long) threadid;
#else
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

#if SIZEOF_PTHREAD_T <= SIZEOF_LONG
	return (long) th;
#else
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

/************************************************************/
#ifdef USE_SEMAPHORES
/************************************************************/

#include <semaphore.h>

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

int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag)
{
	int success;
	sem_t *thelock = &lock->sem;
	int status, error = 0;

	do {
		if (waitflag)
			status = rpythread_fix_status(sem_wait(thelock));
		else
			status = rpythread_fix_status(sem_trywait(thelock));
	} while (status == EINTR); /* Retry if interrupted by a signal */

	if (waitflag) {
		CHECK_STATUS("sem_wait");
	} else if (status != EAGAIN) {
		CHECK_STATUS("sem_trywait");
	}
	
	success = (status == 0) ? 1 : 0;
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
	return 1;
}

void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock)
{
	int status, error = 0;
	if (lock->initialized) {
		status = pthread_mutex_destroy(&lock->mut);
		CHECK_STATUS("pthread_mutex_destroy");

		status = pthread_cond_destroy(&lock->lock_released);
		CHECK_STATUS("pthread_cond_destroy");

		/* 'error' is ignored;
		   CHECK_STATUS already printed an error message */
	}
}

int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag)
{
	int success;
	int status, error = 0;

	status = pthread_mutex_lock( &lock->mut );
	CHECK_STATUS("pthread_mutex_lock[1]");
	success = lock->locked == 0;

	if ( !success && waitflag ) {
		/* continue trying until we get the lock */

		/* mut must be locked by me -- part of the condition
		 * protocol */
		while ( lock->locked ) {
			status = pthread_cond_wait(&lock->lock_released,
						   &lock->mut);
			CHECK_STATUS("pthread_cond_wait");
		}
		success = 1;
	}
	if (success) lock->locked = 1;
	status = pthread_mutex_unlock( &lock->mut );
	CHECK_STATUS("pthread_mutex_unlock[1]");

	if (error) success = 0;
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


/* Thread-local storage */
#define RPyThreadTLS	pthread_key_t

char *RPyThreadTLS_Create(RPyThreadTLS *result)
{
	if (pthread_key_create(result, NULL) != 0)
		return "out of thread-local storage keys";
	else
		return NULL;
}

#define RPyThreadTLS_Get(key)		pthread_getspecific(key)
#define RPyThreadTLS_Set(key, value)	pthread_setspecific(key, value)


#endif /* PYPY_NOT_MAIN_FILE */
