#ifndef _THREAD_NT_H
#define _THREAD_NT_H
#include <WinSock2.h>
#include <windows.h>

/*
 * Thread support.
 */

typedef struct RPyOpaque_ThreadLock {
    HANDLE sem;
} NRMUTEX, *PNRMUTEX;

/* prototypes */
RPY_EXTERN
long RPyThreadStart(void (*func)(void));
RPY_EXTERN
long RPyThreadStartEx(void (*func)(void *), void *arg);
RPY_EXTERN
int RPyThreadLockInit(struct RPyOpaque_ThreadLock *lock);
RPY_EXTERN
void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock);
RPY_EXTERN
int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag);
RPY_EXTERN
RPyLockStatus RPyThreadAcquireLockTimed(struct RPyOpaque_ThreadLock *lock,
					RPY_TIMEOUT_T timeout, int intr_flag);
RPY_EXTERN
long RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock);
RPY_EXTERN
long RPyThreadGetStackSize(void);
RPY_EXTERN
long RPyThreadSetStackSize(long);
#endif


#ifdef _M_IA64
/* On Itanium, use 'acquire' memory ordering semantics */
#define pypy_lock_test_and_set(ptr, value) InterlockedExchangeAcquire(ptr,value)
#else
#define pypy_lock_test_and_set(ptr, value) InterlockedExchange(ptr, value)
#endif
#define pypy_lock_release(ptr)             (*((volatile long *)ptr) = 0)
