#include <windows.h>

/*
 * Thread support.
 */

typedef struct RPyOpaque_ThreadLock {
    HANDLE sem;
} NRMUTEX, *PNRMUTEX;

/* prototypes */
long RPyThreadGetIdent(void);
long RPyThreadStart(void (*func)(void));
int RPyThreadLockInit(struct RPyOpaque_ThreadLock *lock);
void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock);
int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag);
RPyLockStatus RPyThreadAcquireLockTimed(struct RPyOpaque_ThreadLock *lock,
					RPY_TIMEOUT_T timeout, int intr_flag);
void RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock);
long RPyThreadGetStackSize(void);
long RPyThreadSetStackSize(long);

