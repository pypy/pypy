/* Thread-local storage */

#ifdef _WIN32

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
#define RPyThreadStaticTLS_Create(tls)      NULL
#define RPyThreadStaticTLS_Get(tls)         tls
#define RPyThreadStaticTLS_Set(tls, value)  tls = value

#endif

#ifndef RPyThreadStaticTLS

#define RPyThreadStaticTLS             RPyThreadTLS
#define RPyThreadStaticTLS_Create(key) RPyThreadTLS_Create(key)
#define RPyThreadStaticTLS_Get(key)    RPyThreadTLS_Get(key)
#define RPyThreadStaticTLS_Set(key, value) RPyThreadTLS_Set(key, value)
char *RPyThreadTLS_Create(RPyThreadTLS *result);

#endif

