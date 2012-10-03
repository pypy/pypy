#include <windows.h>

/*
 * Thread support.
 */

#define RPyOpaque_INITEXPR_ThreadLock  { 0, 0, NULL }

typedef struct RPyOpaque_ThreadLock {
	LONG   owned ;
	DWORD  thread_id ;
	HANDLE hevent ;
};

/* prototypes */
long RPyThreadStart(void (*func)(void));
int RPyThreadLockInit(struct RPyOpaque_ThreadLock *lock);
void RPyOpaqueDealloc_ThreadLock(struct RPyOpaque_ThreadLock *lock);
int RPyThreadAcquireLock(struct RPyOpaque_ThreadLock *lock, int waitflag);
void RPyThreadReleaseLock(struct RPyOpaque_ThreadLock *lock);
long RPyThreadGetStackSize(void);
long RPyThreadSetStackSize(long);

