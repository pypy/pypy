/* Copy-and-pasted from CPython at 3.10.14
 * by following code paths with !_PY_EMULATED_WIN_CV
 */

#define WIN32_LEAN_AND_MEAN
#include <stdint.h>
#include <stdio.h>
#include <limits.h>
#include <process.h>
#include <windows.h>


/*
 * Thread support.
 */
/* In rpython, this file is pulled in by thread.c */

/* see thread_win7.h */
typedef struct RPyOpaque_ThreadLock NRMUTEX, *PNRMUTEX;

/* -------------------------
 * From Include/pyport.h
 */

   /* enable more aggressive optimization for MSVC */
   /* active in both release and debug builds - see bpo-43271 */
#  pragma optimize("gt", on)
   /* ignore warnings if the compiler decides not to inline a function */
#  pragma warning(disable: 4710)
#  define Py_LOCAL_INLINE(type) static __inline type __fastcall

/* -------------------------
 * From Include/internal/pycore_condvar.h
 */

/* Use native Win7 primitives if build target is Win7 or higher */

/* SRWLOCK is faster and better than CriticalSection */
typedef SRWLOCK PyMUTEX_T;

typedef CONDITION_VARIABLE  PyCOND_T;

/* -------------------------
 * Taken from Python/pytime.c
 */

typedef long long _RPyTime_t;
#define _RPyTime_MAX INT64_MAX
typedef enum {
    _RPyTime_ROUND_FLOOR=0,
    _RPyTime_ROUND_CEILING=1,
    _RPyTime_ROUND_HALF_EVEN=2,
    _RPyTime_ROUND_UP=3,
    _RPyTime_ROUND_TIMEOUT = _RPyTime_ROUND_UP
} _RPyTime_round_t;


static _RPyTime_t
_PyTime_Divide(const _RPyTime_t t, const _RPyTime_t k,
               const _RPyTime_round_t round)
{
    assert(k > 1);
    if (round == _RPyTime_ROUND_HALF_EVEN) {
        _RPyTime_t x, r, abs_r;
        x = t / k;
        r = t % k;
        abs_r = abs(r);
        if (abs_r > k / 2 || (abs_r == k / 2 && (abs(x) & 1))) {
            if (t >= 0) {
                x++;
            }
            else {
                x--;
            }
        }
        return x;
    }
    else if (round == _RPyTime_ROUND_CEILING) {
        if (t >= 0) {
            return (t + k - 1) / k;
        }
        else {
            return t / k;
        }
    }
    else if (round == _RPyTime_ROUND_FLOOR){
        if (t >= 0) {
            return t / k;
        }
        else {
            return (t - (k - 1)) / k;
        }
    }
    else {
        assert(round == _RPyTime_ROUND_UP);
        if (t >= 0) {
            return (t + k - 1) / k;
        }
        else {
            return (t - (k - 1)) / k;
        }
    }
}


static _RPyTime_t
_RPyTime_AsMicroseconds(_RPyTime_t t, _RPyTime_round_t round)
{
    return _PyTime_Divide(t, 1000, round);
}

#define SEC_TO_NS (1000 * 1000 * 1000)

static int
win_perf_counter_frequency(LONGLONG *pfrequency)
{
    LONGLONG frequency;

    LARGE_INTEGER freq;
    if (!QueryPerformanceFrequency(&freq)) {
        return -1;
    }
    frequency = freq.QuadPart;

    /* Sanity check: should never occur in practice */
    if (frequency < 1) {
        return -1;
    }

    if (frequency > _RPyTime_MAX
        || frequency > (LONGLONG)_RPyTime_MAX / (LONGLONG)SEC_TO_NS)
    {
        return -1;
    }

    *pfrequency = frequency;
    return 0;
}

static _RPyTime_t
_PyTime_MulDiv(_RPyTime_t ticks, _RPyTime_t mul, _RPyTime_t div)
{
    _RPyTime_t intpart, remaining;
    /* Compute (ticks * mul / div) in two parts to prevent integer overflow:
       compute integer part, and then the remaining part.

       (ticks * mul) / div == (ticks / div) * mul + (ticks % div) * mul / div

       The caller must ensure that "(div - 1) * mul" cannot overflow. */
    intpart = ticks / div;
    ticks %= div;
    remaining = ticks * mul;
    remaining /= div;
    return intpart * mul + remaining;
}

static int
py_get_win_perf_counter(_RPyTime_t *tp)
{
    static LONGLONG frequency = 0;
    if (frequency == 0) {
        if (win_perf_counter_frequency(&frequency) < 0) {
            return -1;
        }
    }

    LARGE_INTEGER now;
    QueryPerformanceCounter(&now);
    LONGLONG ticksll = now.QuadPart;

    /* Make sure that casting LONGLONG to _RPyTime_t cannot overflow,
 *        both types are signed */
    _RPyTime_t ticks;
    assert(sizeof(ticksll) <= sizeof(ticks));
    ticks = (_RPyTime_t)ticksll;

    *tp = _PyTime_MulDiv(ticks, SEC_TO_NS, (_RPyTime_t)frequency);
    return 0;
}


static _RPyTime_t
_PyTime_GetPerfCounter(void)
{
    _RPyTime_t t;
    int res;
    res = py_get_win_perf_counter(&t);
    if (res  < 0) {
        // If win_perf_counter_frequency() or py_get_monotonic_clock() fails:
        // silently ignore the failure and return 0.
        t = 0;
    }
    return t;
}



/* -------------------------
 * From Python/condvar.h
 */


Py_LOCAL_INLINE(int)
PyMUTEX_INIT(PyMUTEX_T *cs)
{
    InitializeSRWLock(cs);
    return 0;
}

Py_LOCAL_INLINE(int)
PyMUTEX_FINI(PyMUTEX_T *cs)
{
    return 0;
}

Py_LOCAL_INLINE(int)
PyMUTEX_LOCK(PyMUTEX_T *cs)
{
    AcquireSRWLockExclusive(cs);
    return 0;
}

Py_LOCAL_INLINE(int)
PyMUTEX_UNLOCK(PyMUTEX_T *cs)
{
    ReleaseSRWLockExclusive(cs);
    return 0;
}


Py_LOCAL_INLINE(int)
PyCOND_INIT(PyCOND_T *cv)
{
    InitializeConditionVariable(cv);
    return 0;
}
Py_LOCAL_INLINE(int)
PyCOND_FINI(PyCOND_T *cv)
{
    return 0;
}

Py_LOCAL_INLINE(int)
PyCOND_WAIT(PyCOND_T *cv, PyMUTEX_T *cs)
{
    return SleepConditionVariableSRW(cv, cs, INFINITE, 0) ? 0 : -1;
}

/* This implementation makes no distinction about timeouts.  Signal
 * 2 to indicate that we don't know.
 */
Py_LOCAL_INLINE(int)
PyCOND_TIMEDWAIT(PyCOND_T *cv, PyMUTEX_T *cs, long long us)
{
    /* timeout in milliseconds */
    DWORD ms = (DWORD)_PyTime_Divide(us, 1000, _RPyTime_ROUND_TIMEOUT);
    return SleepConditionVariableSRW(cv, cs, ms, 0) != 0 ? 2 : -1;
}

Py_LOCAL_INLINE(int)
PyCOND_SIGNAL(PyCOND_T *cv)
{
     WakeConditionVariable(cv);
     return 0;
}

Py_LOCAL_INLINE(int)
PyCOND_BROADCAST(PyCOND_T *cv)
{
     WakeAllConditionVariable(cv);
     return 0;
}
/* -------------------------
 * Taken from Python/thread_nt.h
 */

#if 0
#define PyMem_RawMalloc malloc
#define PyMem_RawFree free

PNRMUTEX
AllocNonRecursiveMutex()
{
    PNRMUTEX m = (PNRMUTEX)PyMem_RawMalloc(sizeof(NRMUTEX));
    if (!m)
        return NULL;
    if (PyCOND_INIT(&m->cv))
        goto fail;
    if (PyMUTEX_INIT(&m->cs)) {
        PyCOND_FINI(&m->cv);
        goto fail;
    }
    m->locked = 0;
    return m;
fail:
    PyMem_RawFree(m);
    return NULL;
}
VOID
FreeNonRecursiveMutex(PNRMUTEX mutex)
{
    if (mutex) {
        PyCOND_FINI(&mutex->cv);
        PyMUTEX_FINI(&mutex->cs);
        PyMem_RawFree(mutex);
    }
}
#endif

static void gil_fatal(const char *msg, int64_t dw) {
    fprintf(stderr, "Fatal error in the GIL or with locks: %s [%llx,%x]\n",
                    msg, dw, (int)GetLastError());
    abort();
}

DWORD
EnterNonRecursiveMutex(PNRMUTEX mutex, RPY_TIMEOUT_T microseconds)
{
    DWORD result = WAIT_OBJECT_0;
    if (PyMUTEX_LOCK(&mutex->cs))
        return WAIT_FAILED;
    if (microseconds == INFINITE) {
        while (mutex->locked) {
            if (PyCOND_WAIT(&mutex->cv, &mutex->cs)) {
                result = WAIT_FAILED;
                break;
            }
        }
    } else if (microseconds != 0) {
        /* wait at least until the target */
        _RPyTime_t now_ns = _PyTime_GetPerfCounter();
        int line = __LINE__;
        if (now_ns <= 0) {
            gil_fatal("_PyTime_GetPerfCounter() <= 0", (int)now_ns);
        }
        /* This can fail to timeout if microseconds is too big */
        _RPyTime_t target_ns = now_ns + (microseconds * 1000);
        while (mutex->locked) {
            if (PyCOND_TIMEDWAIT(&mutex->cv, &mutex->cs, microseconds) < 0) {
                DWORD err = GetLastError();
                if (err != ERROR_TIMEOUT) {
                    fprintf(stderr, "EnterNonRecursiveMutex failed %d\n", GetLastError());
                    result = WAIT_FAILED;
                    break;
                }
            }
            now_ns = _PyTime_GetPerfCounter();
            if (target_ns <= now_ns)
                break;
            microseconds = _RPyTime_AsMicroseconds(target_ns - now_ns, _RPyTime_ROUND_TIMEOUT);
        }
    }
    if (!mutex->locked) {
        mutex->locked = 1;
        result = WAIT_OBJECT_0;
    } else if (result == WAIT_OBJECT_0)
        result = WAIT_TIMEOUT;
    /* else, it is WAIT_FAILED */
    PyMUTEX_UNLOCK(&mutex->cs); /* must ignore result here */
    return result;
}

BOOL
LeaveNonRecursiveMutex(PNRMUTEX mutex)
{
    BOOL result;
    if (!mutex->locked) {
        return FALSE;
    }
    PyMUTEX_LOCK(&mutex->cs);
    mutex->locked = 0;
    /* condvar APIs return 0 on success. We need to return TRUE on success. */
    PyCOND_SIGNAL(&mutex->cv);
    PyMUTEX_UNLOCK(&mutex->cs);
    return TRUE;
}

typedef struct {
	void (*func)(void *);
	void *arg;
	Signed id;
	HANDLE done;
} callobj;

/* win64: _beginthread takes a UINT so we can store this in a long */
static long _pypythread_stacksize = 0;

static void
bootstrap(void *call)
{
	callobj *obj = (callobj*)call;
	/* copy callobj since other thread might free it before we're done */
	void (*func)(void *) = obj->func;
	void *arg = obj->arg;

	obj->id = (Signed)GetCurrentThreadId();
	if (!ReleaseSemaphore(obj->done, 1, NULL))
        gil_fatal("bootstrap ReleaseSemaphore", 0);
	func(arg);
}

Signed RPyThreadStart(void (*func)(void))
{
    /* a kind-of-invalid cast, but the 'func' passed here doesn't expect
       any argument, so it's unlikely to cause problems */
    return RPyThreadStartEx((void(*)(void *))func, NULL);
}

Signed RPyThreadStartEx(void (*func)(void *), void *arg)
{
	Unsigned rv;
	callobj obj;

	obj.id = -1;	/* guilty until proved innocent */
	obj.func = func;
	obj.arg = arg;
	obj.done = CreateSemaphore(NULL, 0, 1, NULL);
	if (obj.done == NULL)
		return -1;

	rv = _beginthread(bootstrap, _pypythread_stacksize, &obj);
	if (rv == (Unsigned)-1) {
		/* I've seen errno == EAGAIN here, which means "there are
		 * too many threads".
		 */
		obj.id = -1;
	}
	else {
		/* wait for thread to initialize, so we can get its id */
        DWORD res = WaitForSingleObject(obj.done, INFINITE);
        if (res != WAIT_OBJECT_0)
            gil_fatal("WaitForSingleObject(obj.done) failed", res);
        if (obj.id == -1)
            gil_fatal("obj.id == -1", 0);
	}
	CloseHandle((HANDLE)obj.done);
	return obj.id;
}

/************************************************************/
/* PyPy RPython from here
 * but RPyThread* calls are strongly adapted on the thread_nt.h code
 */



/* minimum/maximum thread stack sizes supported */
/* win64: _beginthread takes a UINT, so max must be <4GB.
   It is also stored in a LONG (see above), it must be <2GB.
   The functions below take Signed to simplify Python code. */
#define THREAD_MIN_STACKSIZE    0x8000      /* 32kB */
#define THREAD_MAX_STACKSIZE    0x10000000  /* 256MB */

Signed RPyThreadGetStackSize(void)
{
	return _pypythread_stacksize;
}

Signed RPyThreadSetStackSize(Signed newsize)
{
	if (newsize == 0) {    /* set to default */
		_pypythread_stacksize = 0;
		return 0;
	}

	/* check the range */
	if (newsize >= THREAD_MIN_STACKSIZE && newsize < THREAD_MAX_STACKSIZE) {
	    /* win64: this cast is safe, see THREAD_MAX_STACKSIZE comment */
		_pypythread_stacksize = (long) newsize;
		return 0;
	}
	return -1;
}

unsigned long
RPyThread_get_thread_native_id(void)
{
    DWORD native_id;
    native_id = GetCurrentThreadId();
    return (unsigned long) native_id;
}

/************************************************************/



void RPyThreadAfterFork(void)
{
}

int RPyThreadLockInit(struct RPyOpaque_ThreadLock *lock)
{
    /* In upstream this is AllocNonRecursiveMutex */
    if (!lock)
        return -1;
    if (PyCOND_INIT(&lock->cv))
        return -2;
    if (PyMUTEX_INIT(&lock->cs)) {
        PyCOND_FINI(&lock->cv);
        return -3;
    }
    lock->locked = 0;
    return 1;
}

void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *mutex)
{
	/* FreeNonRecursiveMutex(lock) without the "free" */
    if (mutex) {
        PyCOND_FINI(&mutex->cv);
        PyMUTEX_FINI(&mutex->cs);
    }
}

/*
 * Return 1 on success if the lock was acquired
 *
 * and 0 if the lock was not acquired. This means a 0 is returned
 * if the lock has already been acquired by this thread!
 */
RPyLockStatus
RPyThreadAcquireLockTimed(struct RPyOpaque_ThreadLock *aLock,
			  RPY_TIMEOUT_T microseconds, int intr_flag)
{
    /* Fow now, intr_flag does nothing on Windows, and lock acquires are
     * uninterruptible.  */
    RPyLockStatus success;

    if (microseconds < 0) {
        microseconds = INFINITE;
    }
    if (aLock && EnterNonRecursiveMutex((PNRMUTEX)aLock,
                                        microseconds) == WAIT_OBJECT_0) {
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

Signed RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock)
{
    if (LeaveNonRecursiveMutex(lock))
        return 0;   /* success */
    else
        return -1;  /* failure: the lock was not previously acquired */
}

/************************************************************/
/* GIL code                                                 */
/************************************************************/

#define ASSERT_STATUS(call)                             \
    if (call != 0) {                                    \
        fprintf(stderr, "Fatal error: " #call);         \
        abort();                                        \
    }


typedef PyMUTEX_T mutex1_t;

static INLINE void mutex1_init(mutex1_t *mutex) {
    ASSERT_STATUS(PyMUTEX_INIT(mutex));
}

static INLINE void mutex1_lock(mutex1_t *mutex) {
    ASSERT_STATUS(PyMUTEX_LOCK(mutex));
}

static INLINE void mutex1_unlock(mutex1_t *mutex) {
    ASSERT_STATUS(PyMUTEX_UNLOCK(mutex));
}

typedef NRMUTEX mutex2_t; 

static INLINE void mutex2_init_locked(mutex2_t *mutex) {
    mutex->locked = 1;
    ASSERT_STATUS(PyCOND_INIT(&mutex->cv));
    ASSERT_STATUS(PyMUTEX_INIT(&mutex->cs));
}

static INLINE void mutex2_unlock(mutex2_t *mutex) {
    ASSERT_STATUS(PyMUTEX_LOCK(&mutex->cs));
    mutex->locked = 0;
    ASSERT_STATUS(PyMUTEX_UNLOCK(&mutex->cs));
    PyCOND_SIGNAL(&mutex->cv);
}

static INLINE void mutex2_loop_start(mutex2_t *mutex) {
    ASSERT_STATUS(PyMUTEX_LOCK(&mutex->cs));
}
static INLINE void mutex2_loop_stop(mutex2_t *mutex) {
    ASSERT_STATUS(PyMUTEX_UNLOCK(&mutex->cs));
}

static INLINE int mutex2_lock_timeout(mutex2_t *mutex, double delay)
{
    if (mutex->locked) {
        /* delay in seconds */
        DWORD ms = (DWORD)(delay * 1000.0 + 0.999);
        int error_from_timedwait = SleepConditionVariableSRW(&mutex->cv, &mutex->cs, ms, 0);
        if (error_from_timedwait == 0) {
            DWORD err = GetLastError();
            if (err != ERROR_TIMEOUT) {
                ASSERT_STATUS(error_from_timedwait);
            }
        }
    }
    int result = !mutex->locked;
    mutex->locked = 1;
    return result;
}

//#define pypy_lock_test_and_set(ptr, value)  see thread_nt.h
#ifdef _WIN64
#define atomic_increment(ptr)          InterlockedIncrement64(ptr)
#define atomic_decrement(ptr)          InterlockedDecrement64(ptr)
#else
#define atomic_increment(ptr)          InterlockedIncrement(ptr)
#define atomic_decrement(ptr)          InterlockedDecrement(ptr)
#endif
#ifdef YieldProcessor
#  define RPy_YieldProcessor()         YieldProcessor()
#else
#  define RPy_YieldProcessor()         __asm { rep nop }
#endif
#define RPy_CompilerMemoryBarrier()    _ReadWriteBarrier()

#include "src/thread_gil.c"
