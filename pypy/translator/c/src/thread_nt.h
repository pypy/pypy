/* Copy-and-pasted from CPython */

/* This code implemented by Dag.Gruneau@elsa.preseco.comm.se */
/* Fast NonRecursiveMutex support by Yakov Markovitch, markovitch@iso.ru */
/* Eliminated some memory leaks, gsw@agere.com */

#include <windows.h>
#include <limits.h>
#include <process.h>


/*
 * Thread support.
 */

#define RPyOpaque_INITEXPR_ThreadLock  { 0, 0, NULL }

typedef struct {
	void (*func)(void);
	long id;
	HANDLE done;
} callobj;

typedef struct RPyOpaque_ThreadLock {
	LONG   owned ;
	DWORD  thread_id ;
	HANDLE hevent ;
} NRMUTEX, *PNRMUTEX ;

/* prototypes */
long RPyThreadStart(void (*func)(void));
BOOL InitializeNonRecursiveMutex(PNRMUTEX mutex);
VOID DeleteNonRecursiveMutex(PNRMUTEX mutex);
DWORD EnterNonRecursiveMutex(PNRMUTEX mutex, BOOL wait);
BOOL LeaveNonRecursiveMutex(PNRMUTEX mutex);
void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock);
int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag);
void RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock);
long RPyThreadGetStackSize(void);
long RPyThreadSetStackSize(long);


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

static long _pypythread_stacksize = 0;

/*
 * Return the thread Id instead of an handle. The Id is said to uniquely
   identify the thread in the system
 */
int RPyThreadGetIdent()
{
  return GetCurrentThreadId();
}

static void
bootstrap(void *call)
{
	callobj *obj = (callobj*)call;
	/* copy callobj since other thread might free it before we're done */
	void (*func)(void) = obj->func;

	obj->id = RPyThreadGetIdent();
	ReleaseSemaphore(obj->done, 1, NULL);
	func();
}

long RPyThreadStart(void (*func)(void))
{
	unsigned long rv;
	callobj obj;

	obj.id = -1;	/* guilty until proved innocent */
	obj.func = func;
	obj.done = CreateSemaphore(NULL, 0, 1, NULL);
	if (obj.done == NULL)
		return -1;

	rv = _beginthread(bootstrap, _pypythread_stacksize, &obj);
	if (rv == (unsigned long)-1) {
		/* I've seen errno == EAGAIN here, which means "there are
		 * too many threads".
		 */
		obj.id = -1;
	}
	else {
		/* wait for thread to initialize, so we can get its id */
		WaitForSingleObject(obj.done, INFINITE);
		assert(obj.id != -1);
	}
	CloseHandle((HANDLE)obj.done);
	return obj.id;
}

/************************************************************/

/* minimum/maximum thread stack sizes supported */
#define THREAD_MIN_STACKSIZE    0x8000      /* 32kB */
#define THREAD_MAX_STACKSIZE    0x10000000  /* 256MB */

long RPyThreadGetStackSize(void)
{
	return _pypythread_stacksize;
}

long RPyThreadSetStackSize(long newsize)
{
	if (newsize == 0) {    /* set to default */
		_pypythread_stacksize = 0;
		return 0;
	}

	/* check the range */
	if (newsize >= THREAD_MIN_STACKSIZE && newsize < THREAD_MAX_STACKSIZE) {
		_pypythread_stacksize = newsize;
		return 0;
	}
	return -1;
}

/************************************************************/


BOOL InitializeNonRecursiveMutex(PNRMUTEX mutex)
{
	mutex->owned = -1 ;  /* No threads have entered NonRecursiveMutex */
	mutex->thread_id = 0 ;
	mutex->hevent = CreateEvent(NULL, FALSE, FALSE, NULL) ;
	return mutex->hevent != NULL ;	/* TRUE if the mutex is created */
}

VOID DeleteNonRecursiveMutex(PNRMUTEX mutex)
{
	/* No in-use check */
	CloseHandle(mutex->hevent) ;
	mutex->hevent = NULL ; /* Just in case */
}

DWORD EnterNonRecursiveMutex(PNRMUTEX mutex, BOOL wait)
{
	/* Assume that the thread waits successfully */
	DWORD ret ;

	/* InterlockedIncrement(&mutex->owned) == 0 means that no thread currently owns the mutex */
	if (!wait)
	{
		if (InterlockedCompareExchange(&mutex->owned, 0, -1) != -1)
			return WAIT_TIMEOUT ;
		ret = WAIT_OBJECT_0 ;
	}
	else
		ret = InterlockedIncrement(&mutex->owned) ?
			/* Some thread owns the mutex, let's wait... */
			WaitForSingleObject(mutex->hevent, INFINITE) : WAIT_OBJECT_0 ;

	mutex->thread_id = GetCurrentThreadId() ; /* We own it */
	return ret ;
}

BOOL LeaveNonRecursiveMutex(PNRMUTEX mutex)
{
	/* We don't own the mutex */
	mutex->thread_id = 0 ;
	return
		InterlockedDecrement(&mutex->owned) < 0 ||
		SetEvent(mutex->hevent) ; /* Other threads are waiting, wake one on them up */
}

/************************************************************/

void RPyThreadAfterFork(void)
{
}

int RPyThreadLockInit(struct RPyOpaque_ThreadLock * lock)
{
  return InitializeNonRecursiveMutex(lock);
}

void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock)
{
	if (lock->hevent != NULL)
		DeleteNonRecursiveMutex(lock);
}

/*
 * Return 1 on success if the lock was acquired
 *
 * and 0 if the lock was not acquired. This means a 0 is returned
 * if the lock has already been acquired by this thread!
 */
int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag)
{
	return EnterNonRecursiveMutex(lock, (waitflag != 0 ? INFINITE : 0)) == WAIT_OBJECT_0;
}

void RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock)
{
	if (!LeaveNonRecursiveMutex(lock))
		/* XXX complain? */;
}

/************************************************************/

/* Thread-local storage */
#define RPyThreadTLS	DWORD
#define __thread __declspec(thread)

char *RPyThreadTLS_Create(RPyThreadTLS *result)
{
	*result = TlsAlloc();
	if (*result == TLS_OUT_OF_INDEXES)
		return "out of thread-local storage indexes";
	else
		return NULL;
}

#define RPyThreadTLS_Get(key)		TlsGetValue(key)
#define RPyThreadTLS_Set(key, value)	TlsSetValue(key, value)


/************************************************************/
/* GIL code                                                 */
/************************************************************/

static volatile LONG pending_acquires = -1;
static CRITICAL_SECTION mutex_gil;
static HANDLE cond_gil;

long RPyGilAllocate(void)
{
    pending_acquires = 0;
    InitializeCriticalSection(&mutex_gil);
    EnterCriticalSection(&mutex_gil);
    cond_gil = CreateEvent (NULL, FALSE, FALSE, NULL);
    return 1;
}

long RPyGilYieldThread(void)
{
    /* can be called even before RPyGilAllocate(), but in this case,
       pending_acquires will be -1 */
    if (pending_acquires <= 0)
        return 0;
    InterlockedIncrement(&pending_acquires);
    PulseEvent(cond_gil);

    /* hack: the three following lines do a pthread_cond_wait(), and
       normally specifying a timeout of INFINITE would be fine.  But the
       first and second operations are not done atomically, so there is a
       (small) risk that PulseEvent misses the WaitForSingleObject().
       In this case the process will just sleep a few milliseconds. */
    LeaveCriticalSection(&mutex_gil);
    WaitForSingleObject(cond_gil, 15);
    EnterCriticalSection(&mutex_gil);

    InterlockedDecrement(&pending_acquires);
    return 1;
}

void RPyGilRelease(void)
{
    LeaveCriticalSection(&mutex_gil);
    PulseEvent(cond_gil);
}

void RPyGilAcquire(void)
{
    InterlockedIncrement(&pending_acquires);
    EnterCriticalSection(&mutex_gil);
    InterlockedDecrement(&pending_acquires);
}


#endif /* PYPY_NOT_MAIN_FILE */
