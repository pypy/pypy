/* Copy-and-pasted from CPython */

/* This code implemented by Dag.Gruneau@elsa.preseco.comm.se */
/* Fast NonRecursiveMutex support by Yakov Markovitch, markovitch@iso.ru */
/* Eliminated some memory leaks, gsw@agere.com */

/* Windows.h includes winsock.h, but the socket module needs */ 
/* winsock2.h. So I include it before. Ugly. */

#include <winsock2.h>
#include <ws2tcpip.h>

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


/* implementations */

#ifndef PYPY_NOT_MAIN_FILE

/*
 * Return the thread Id instead of an handle. The Id is said to uniquely
   identify the thread in the system
 */
int RPyThreadGetIdent()
{
  return GetCurrentThreadId();
}

static int
bootstrap(void *call)
{
	callobj *obj = (callobj*)call;
	/* copy callobj since other thread might free it before we're done */
	void (*func)(void) = obj->func;

	obj->id = RPyThreadGetIdent();
	ReleaseSemaphore(obj->done, 1, NULL);
	func();
	return 0;
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

	rv = _beginthread(bootstrap, 0, &obj); /* use default stack size */
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


typedef PVOID WINAPI interlocked_cmp_xchg_t(PVOID *dest, PVOID exc, PVOID comperand) ;

/* Sorry mate, but we haven't got InterlockedCompareExchange in Win95! */
static PVOID WINAPI interlocked_cmp_xchg(PVOID *dest, PVOID exc, PVOID comperand)
{
	static LONG spinlock = 0 ;
	PVOID result ;
	DWORD dwSleep = 0;

	/* Acqire spinlock (yielding control to other threads if cant aquire for the moment) */
	while(InterlockedExchange(&spinlock, 1))
	{
		// Using Sleep(0) can cause a priority inversion.
		// Sleep(0) only yields the processor if there's
		// another thread of the same priority that's
		// ready to run.  If a high-priority thread is
		// trying to acquire the lock, which is held by
		// a low-priority thread, then the low-priority
		// thread may never get scheduled and hence never
		// free the lock.  NT attempts to avoid priority
		// inversions by temporarily boosting the priority
		// of low-priority runnable threads, but the problem
		// can still occur if there's a medium-priority
		// thread that's always runnable.  If Sleep(1) is used,
		// then the thread unconditionally yields the CPU.  We
		// only do this for the second and subsequent even
		// iterations, since a millisecond is a long time to wait
		// if the thread can be scheduled in again sooner
		// (~100,000 instructions).
		// Avoid priority inversion: 0, 1, 0, 1,...
		Sleep(dwSleep);
		dwSleep = !dwSleep;
	}
	result = *dest ;
	if (result == comperand)
		*dest = exc ;
	/* Release spinlock */
	spinlock = 0 ;
	return result ;
} ;

static interlocked_cmp_xchg_t *ixchg ;
BOOL InitializeNonRecursiveMutex(PNRMUTEX mutex)
{
	if (!ixchg)
	{
		/* Sorely, Win95 has no InterlockedCompareExchange API (Win98 has), so we have to use emulation */
		HANDLE kernel = GetModuleHandle("kernel32.dll") ;
		if (!kernel || (ixchg = (interlocked_cmp_xchg_t *)GetProcAddress(kernel, "InterlockedCompareExchange")) == NULL)
			ixchg = interlocked_cmp_xchg ;
	}

	mutex->owned = -1 ;  /* No threads have entered NonRecursiveMutex */
	mutex->thread_id = 0 ;
	mutex->hevent = CreateEvent(NULL, FALSE, FALSE, NULL) ;
	return mutex->hevent != NULL ;	/* TRUE if the mutex is created */
}

#ifdef InterlockedCompareExchange
#undef InterlockedCompareExchange
#endif
#define InterlockedCompareExchange(dest,exchange,comperand) (ixchg((dest), (exchange), (comperand)))

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
		if (InterlockedCompareExchange((PVOID *)&mutex->owned, (PVOID)0, (PVOID)-1) != (PVOID)-1)
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


#endif /* PYPY_NOT_MAIN_FILE */
