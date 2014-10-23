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
RPY_EXPORTED_FOR_TESTS
long RPyThreadGetIdent(void);
RPY_EXPORTED_FOR_TESTS
long RPyThreadStart(void (*func)(void));
RPY_EXPORTED_FOR_TESTS
int RPyThreadLockInit(struct RPyOpaque_ThreadLock *lock);
RPY_EXPORTED_FOR_TESTS
void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock);
RPY_EXPORTED_FOR_TESTS
int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag);
RPY_EXPORTED_FOR_TESTS
RPyLockStatus RPyThreadAcquireLockTimed(struct RPyOpaque_ThreadLock *lock,
					RPY_TIMEOUT_T timeout, int intr_flag);
RPY_EXPORTED_FOR_TESTS
void RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock);
RPY_EXPORTED_FOR_TESTS
long RPyThreadGetStackSize(void);
RPY_EXPORTED_FOR_TESTS
long RPyThreadSetStackSize(long);
#endif
