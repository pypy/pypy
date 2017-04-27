# This file is dual licensed under the terms of the Apache License, Version
# 2.0, and the BSD License. See the LICENSE file in the root of this repository
# for complete details.

from __future__ import absolute_import, division, print_function

import sys

import cffi

INCLUDES = """
#include <openssl/ssl.h>
#include <openssl/x509.h>
#include <openssl/x509_vfy.h>
#include <openssl/crypto.h>
"""

TYPES = """
static const long Cryptography_STATIC_CALLBACKS;

/* crypto.h
 * CRYPTO_set_locking_callback
 * void (*cb)(int mode, int type, const char *file, int line)
 */
extern "Python" void Cryptography_locking_cb(int, int, const char *, int);

/* pem.h
 * int pem_password_cb(char *buf, int size, int rwflag, void *userdata);
 */
extern "Python" int Cryptography_pem_password_cb(char *, int, int, void *);

/* rand.h
 * int (*bytes)(unsigned char *buf, int num);
 * int (*status)(void);
 */
extern "Python" int Cryptography_rand_bytes(unsigned char *, int);
extern "Python" int Cryptography_rand_status(void);
"""

FUNCTIONS = """
int _setup_ssl_threads(void);
"""

MACROS = """
"""

CUSTOMIZATIONS = """
static const long Cryptography_STATIC_CALLBACKS = 1;
"""

if cffi.__version_info__ < (1, 4, 0) or sys.version_info >= (3, 5):
    # backwards compatibility for old cffi version on PyPy
    # and Python >=3.5 (https://github.com/pyca/cryptography/issues/2970)
    TYPES = "static const long Cryptography_STATIC_CALLBACKS;"
    CUSTOMIZATIONS = """static const long Cryptography_STATIC_CALLBACKS = 0;
"""

CUSTOMIZATIONS += """
/* This code is derived from the locking code found in the Python _ssl module's
   locking callback for OpenSSL.

   Copyright 2001-2016 Python Software Foundation; All Rights Reserved.
*/

#ifdef _WIN32
#ifdef _MSC_VER
#ifdef inline
#undef inline
#endif
#define inline __inline
#endif
#include <Windows.h>
typedef CRITICAL_SECTION mutex1_t;
static inline void mutex1_init(mutex1_t *mutex) {
    InitializeCriticalSection(mutex);
}
static inline void mutex1_lock(mutex1_t *mutex) {
    EnterCriticalSection(mutex);
}
static inline void mutex1_unlock(mutex1_t *mutex) {
    LeaveCriticalSection(mutex);
}
#else
#include <stdio.h>
#include <stdlib.h>
#include <pthread.h>
typedef pthread_mutex_t mutex1_t;
#define ASSERT_STATUS(call)                             \
    if (call != 0) {                                    \
        perror("Fatal error in _cffi_ssl: " #call);     \
        abort();                                        \
    }
static inline void mutex1_init(mutex1_t *mutex) {
#if !defined(pthread_mutexattr_default)
#  define pthread_mutexattr_default ((pthread_mutexattr_t *)NULL)
#endif
    ASSERT_STATUS(pthread_mutex_init(mutex, pthread_mutexattr_default));
}
static inline void mutex1_lock(mutex1_t *mutex) {
    ASSERT_STATUS(pthread_mutex_lock(mutex));
}
static inline void mutex1_unlock(mutex1_t *mutex) {
    ASSERT_STATUS(pthread_mutex_unlock(mutex));
}
#endif

static unsigned int _ssl_locks_count = 0;
static mutex1_t *_ssl_locks = NULL;

static void _ssl_thread_locking_function(int mode, int n, const char *file,
                                         int line) {
    /* this function is needed to perform locking on shared data
       structures. (Note that OpenSSL uses a number of global data
       structures that will be implicitly shared whenever multiple
       threads use OpenSSL.) Multi-threaded applications will
       crash at random if it is not set.

       locking_function() must be able to handle up to
       CRYPTO_num_locks() different mutex locks. It sets the n-th
       lock if mode & CRYPTO_LOCK, and releases it otherwise.

       file and line are the file number of the function setting the
       lock. They can be useful for debugging.
    */

    if ((_ssl_locks == NULL) ||
        (n < 0) || ((unsigned)n >= _ssl_locks_count)) {
        return;
    }

    if (mode & CRYPTO_LOCK) {
        mutex1_lock(_ssl_locks + n);
    } else {
        mutex1_unlock(_ssl_locks + n);
    }
}

static void init_mutexes(void)
{
    int i;
    for (i = 0;  i < _ssl_locks_count;  i++) {
        mutex1_init(_ssl_locks + i);
    }
}

int _setup_ssl_threads(void) {
    if (_ssl_locks == NULL) {
        _ssl_locks_count = CRYPTO_num_locks();
        _ssl_locks = malloc(sizeof(mutex1_t) * _ssl_locks_count);
        if (_ssl_locks == NULL) {
            return 0;
        }
        init_mutexes();
        CRYPTO_set_locking_callback(_ssl_thread_locking_function);
#ifndef _WIN32
        pthread_atfork(NULL, NULL, &init_mutexes);
#endif
    }
    return 1;
}
"""
