#include "src/threadlocal.h"

#ifdef _WIN32

char *RPyThreadTLS_Create(RPyThreadTLS *result)
{
    *result = TlsAlloc();
    if (*result == TLS_OUT_OF_INDEXES)
        return "out of thread-local storage indexes";
    else
        return NULL;
}

#else

char *RPyThreadTLS_Create(RPyThreadTLS *result)
{
    if (pthread_key_create(result, NULL) != 0)
        return "out of thread-local storage keys";
    else
        return NULL;
}

#endif
