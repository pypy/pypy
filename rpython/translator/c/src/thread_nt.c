/* Copy-and-pasted from CPython */

/* This code implemented by Dag.Gruneau@elsa.preseco.comm.se */
/* Fast NonRecursiveMutex support by Yakov Markovitch, markovitch@iso.ru */
/* Eliminated some memory leaks, gsw@agere.com */

#include <windows.h>
#include <stdio.h>
#include <limits.h>
#include <process.h>


/*
 * Thread support.
 */
/* In rpython, this file is pulled in by thread.c */

typedef struct RPyOpaque_ThreadLock NRMUTEX, *PNRMUTEX;

typedef struct {
	void (*func)(void);
	long id;
	HANDLE done;
} callobj;

static long _pypythread_stacksize = 0;

/*
 * Return the thread Id instead of an handle. The Id is said to uniquely
   identify the thread in the system
 */
long RPyThreadGetIdent()
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
    mutex->sem = CreateSemaphore(NULL, 1, 1, NULL);
    return !!mutex->sem;
}

VOID DeleteNonRecursiveMutex(PNRMUTEX mutex)
{
    /* No in-use check */
    CloseHandle(mutex->sem);
    mutex->sem = NULL ; /* Just in case */
}

DWORD EnterNonRecursiveMutex(PNRMUTEX mutex, DWORD milliseconds)
{
    return WaitForSingleObject(mutex->sem, milliseconds);
}

BOOL LeaveNonRecursiveMutex(PNRMUTEX mutex)
{
    return ReleaseSemaphore(mutex->sem, 1, NULL);
}

/************************************************************/

void RPyThreadAfterFork(void)
{
}

int RPyThreadLockInit(struct RPyOpaque_ThreadLock *lock)
{
  return InitializeNonRecursiveMutex(lock);
}

void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock)
{
    if (lock->sem != NULL)
	DeleteNonRecursiveMutex(lock);
}

/*
 * Return 1 on success if the lock was acquired
 *
 * and 0 if the lock was not acquired. This means a 0 is returned
 * if the lock has already been acquired by this thread!
 */
RPyLockStatus
RPyThreadAcquireLockTimed(struct RPyOpaque_ThreadLock *lock,
			  RPY_TIMEOUT_T microseconds, int intr_flag)
{
    /* Fow now, intr_flag does nothing on Windows, and lock acquires are
     * uninterruptible.  */
    RPyLockStatus success;
    RPY_TIMEOUT_T milliseconds;

    if (microseconds >= 0) {
        milliseconds = microseconds / 1000;
        if (microseconds % 1000 > 0)
            ++milliseconds;
        if ((DWORD) milliseconds != milliseconds) {
            fprintf(stderr, "Timeout too large for a DWORD, "
                            "please check RPY_TIMEOUT_MAX");
            abort();
        }
    }
    else
        milliseconds = INFINITE;

    if (lock && EnterNonRecursiveMutex(
	    lock, (DWORD)milliseconds) == WAIT_OBJECT_0) {
        success = RPY_LOCK_ACQUIRED;
    }
    else {
        success = RPY_LOCK_FAILURE;
    }

    return success;
}

int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag)
{
    return RPyThreadAcquireLockTimed(lock, waitflag ? -1 : 0, /*intr_flag=*/0);
}

void RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock)
{
	if (!LeaveNonRecursiveMutex(lock))
		/* XXX complain? */;
}

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

#ifdef RPY_FASTGIL
# error "XXX implement me"
InterlockedExchangePointer
#endif
