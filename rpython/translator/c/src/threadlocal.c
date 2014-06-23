#include <stdio.h>
#include <stdlib.h>
#include "src/threadlocal.h"

#ifdef _WIN32

void RPyThreadTLS_Create(RPyThreadTLS *result)
{
    *result = TlsAlloc();
    if (*result == TLS_OUT_OF_INDEXES) {
        fprintf(stderr, "Internal RPython error: "
                        "out of thread-local storage indexes");
        abort();
    }
}

#else

void RPyThreadTLS_Create(RPyThreadTLS *result)
{
    if (pthread_key_create(result, NULL) != 0) {
        fprintf(stderr, "Internal RPython error: "
                        "out of thread-local storage keys");
        abort();
    }
}

#endif
