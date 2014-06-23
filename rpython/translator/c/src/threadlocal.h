/* Thread-local storage */
#ifndef _SRC_THREADLOCAL_H
#define _SRC_THREADLOCAL_H


#ifdef _WIN32

#include <WinSock2.h>
#include <windows.h>
#define __thread __declspec(thread)
typedef DWORD RPyThreadTLS;
#define RPyThreadTLS_Get(key)		TlsGetValue(key)
#define RPyThreadTLS_Set(key, value)	TlsSetValue(key, value)

#else

#include <pthread.h>
typedef pthread_key_t RPyThreadTLS;
#define RPyThreadTLS_Get(key)		pthread_getspecific(key)
#define RPyThreadTLS_Set(key, value)	pthread_setspecific(key, value)

#endif


#ifdef USE___THREAD

#define RPyThreadStaticTLS                  __thread void *
#define RPyThreadStaticTLS_Create(tls)      (void)0
#define RPyThreadStaticTLS_Get(tls)         tls
#define RPyThreadStaticTLS_Set(tls, value)  tls = value
#define OP_THREADLOCALREF_GETADDR(tlref, ptr)  ptr = tlref

#endif

#ifndef RPyThreadStaticTLS

#define RPyThreadStaticTLS             RPyThreadTLS
#define RPyThreadStaticTLS_Create(key) RPyThreadTLS_Create(key)
#define RPyThreadStaticTLS_Get(key)    RPyThreadTLS_Get(key)
#define RPyThreadStaticTLS_Set(key, value) RPyThreadTLS_Set(key, value)
void RPyThreadTLS_Create(RPyThreadTLS *result);

#endif


#define OP_THREADLOCALREF_SET(tlref, ptr, _) RPyThreadStaticTLS_Set(*tlref, ptr)
#define OP_THREADLOCALREF_GET(tlref, ptr)   ptr = RPyThreadStaticTLS_Get(*tlref)


#endif /* _SRC_THREADLOCAL_H */
