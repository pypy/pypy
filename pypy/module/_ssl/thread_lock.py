from rpython.rlib import rthread
from rpython.rlib.ropenssl import libraries
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.translator.tool.cbuild import ExternalCompilationInfo

# CRYPTO_set_locking_callback:
#
# this function is needed to perform locking on shared data
# structures. (Note that OpenSSL uses a number of global data
# structures that will be implicitly shared whenever multiple threads
# use OpenSSL.) Multi-threaded applications will crash at random if
# it is not set.
#
# locking_function() must be able to handle up to CRYPTO_num_locks()
# different mutex locks. It sets the n-th lock if mode & CRYPTO_LOCK, and
# releases it otherwise.
#
# filename and line are the file number of the function setting the
# lock. They can be useful for debugging.


# This logic is moved to C code so that the callbacks can be invoked
# without caring about the GIL.

separate_module_source = """
#include <openssl/crypto.h>

static unsigned int _ssl_locks_count = 0;
static struct RPyOpaque_ThreadLock *_ssl_locks;

static unsigned long _ssl_thread_id_function(void) {
    return RPyThreadGetIdent();
}

static void _ssl_thread_locking_function(int mode, int n, const char *file,
                                         int line) {
    if ((_ssl_locks == NULL) ||
        (n < 0) || ((unsigned)n >= _ssl_locks_count))
        return;

    if (mode & CRYPTO_LOCK) {
        RPyThreadAcquireLock(_ssl_locks + n, 1);
    } else {
        RPyThreadReleaseLock(_ssl_locks + n);
    }
}

int _PyPy_SSL_SetupThreads(void)
{
    unsigned int i;
    _ssl_locks_count = CRYPTO_num_locks();
    _ssl_locks = calloc(_ssl_locks_count, sizeof(struct RPyOpaque_ThreadLock));
    if (_ssl_locks == NULL)
        return 0;
    for (i=0; i<_ssl_locks_count; i++) {
        if (RPyThreadLockInit(_ssl_locks + i) == 0)
            return 0;
    }
    CRYPTO_set_locking_callback(_ssl_thread_locking_function);
    CRYPTO_set_id_callback(_ssl_thread_id_function);
    return 1;
}
"""

eci = rthread.eci.merge(ExternalCompilationInfo(
    separate_module_sources=[separate_module_source],
    post_include_bits=[
        "int _PyPy_SSL_SetupThreads(void);"],
    export_symbols=['_PyPy_SSL_SetupThreads'],
    libraries = libraries,
))

_PyPy_SSL_SetupThreads = rffi.llexternal('_PyPy_SSL_SetupThreads',
                                         [], rffi.INT,
                                         compilation_info=eci)

def setup_ssl_threads():
    result = _PyPy_SSL_SetupThreads()
    if rffi.cast(lltype.Signed, result) == 0:
        raise MemoryError
