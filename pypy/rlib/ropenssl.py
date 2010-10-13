from pypy.rpython.lltypesystem import rffi, lltype
from pypy.rpython.tool import rffi_platform
from pypy.translator.platform import platform
from pypy.translator.tool.cbuild import ExternalCompilationInfo

import sys

if sys.platform == 'win32' and platform.name != 'mingw32':
    libraries = ['libeay32', 'ssleay32', 'user32', 'advapi32', 'gdi32']
    includes = [
        # ssl.h includes winsock.h, which will conflict with our own
        # need of winsock2.  Remove this when separate compilation is
        # available...
        'winsock2.h',
        # wincrypt.h defines X509_NAME, include it here
        # so that openssl/ssl.h can repair this nonsense.
        'wincrypt.h',
        'openssl/ssl.h',
        'openssl/err.h']
else:
    libraries = ['ssl', 'crypto']
    includes = ['openssl/ssl.h', 'openssl/err.h']

eci = ExternalCompilationInfo(
    libraries = libraries,
    includes = includes,
    export_symbols = ['SSL_load_error_strings'],
    )

eci = rffi_platform.configure_external_library(
    'openssl', eci,
    [dict(prefix='openssl-',
          include_dir='inc32', library_dir='out32'),
     ])

## user defined constants
X509_NAME_MAXLEN = 256
## # these mirror ssl.h
PY_SSL_ERROR_NONE, PY_SSL_ERROR_SSL = 0, 1
PY_SSL_ERROR_WANT_READ, PY_SSL_ERROR_WANT_WRITE = 2, 3
PY_SSL_ERROR_WANT_X509_LOOKUP = 4
PY_SSL_ERROR_SYSCALL = 5 # look at error stack/return value/errno
PY_SSL_ERROR_ZERO_RETURN, PY_SSL_ERROR_WANT_CONNECT = 6, 7
# start of non ssl.h errorcodes
PY_SSL_ERROR_EOF = 8 # special case of SSL_ERROR_SYSCALL
PY_SSL_ERROR_INVALID_ERROR_CODE = 9

PY_SSL_CERT_NONE, PY_SSL_CERT_OPTIONAL, PY_SSL_CERT_REQUIRED = 0, 1, 2

(PY_SSL_VERSION_SSL2, PY_SSL_VERSION_SSL3,
 PY_SSL_VERSION_SSL23, PY_SSL_VERSION_TLS1) = range(4)

SOCKET_IS_NONBLOCKING, SOCKET_IS_BLOCKING = 0, 1
SOCKET_HAS_TIMED_OUT, SOCKET_HAS_BEEN_CLOSED = 2, 3
SOCKET_TOO_LARGE_FOR_SELECT, SOCKET_OPERATION_OK = 4, 5

# WinSock does not use a bitmask in select, and uses
# socket handles greater than FD_SETSIZE
if sys.platform == 'win32':
    MAX_FD_SIZE = None
else:
    from pypy.rlib._rsocket_rffi import FD_SETSIZE as MAX_FD_SIZE

HAVE_RPOLL = True  # Even win32 has rpoll.poll

class CConfig:
    _compilation_info_ = eci

    OPENSSL_VERSION_NUMBER = rffi_platform.ConstantInteger(
        "OPENSSL_VERSION_NUMBER")
    SSLEAY_VERSION = rffi_platform.DefinedConstantString(
        "SSLEAY_VERSION", "SSLeay_version(SSLEAY_VERSION)")
    SSL_FILETYPE_PEM = rffi_platform.ConstantInteger("SSL_FILETYPE_PEM")
    SSL_OP_ALL = rffi_platform.ConstantInteger("SSL_OP_ALL")
    SSL_VERIFY_NONE = rffi_platform.ConstantInteger("SSL_VERIFY_NONE")
    SSL_ERROR_WANT_READ = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_READ")
    SSL_ERROR_WANT_WRITE = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_WRITE")
    SSL_ERROR_ZERO_RETURN = rffi_platform.ConstantInteger(
        "SSL_ERROR_ZERO_RETURN")
    SSL_ERROR_WANT_X509_LOOKUP = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_X509_LOOKUP")
    SSL_ERROR_WANT_CONNECT = rffi_platform.ConstantInteger(
        "SSL_ERROR_WANT_CONNECT")
    SSL_ERROR_SYSCALL = rffi_platform.ConstantInteger("SSL_ERROR_SYSCALL")
    SSL_ERROR_SSL = rffi_platform.ConstantInteger("SSL_ERROR_SSL")
    SSL_CTRL_OPTIONS = rffi_platform.ConstantInteger("SSL_CTRL_OPTIONS")
    BIO_C_SET_NBIO = rffi_platform.ConstantInteger("BIO_C_SET_NBIO")

for k, v in rffi_platform.configure(CConfig).items():
    globals()[k] = v

# opaque structures
SSL_METHOD = rffi.COpaquePtr('SSL_METHOD')
SSL_CTX = rffi.COpaquePtr('SSL_CTX')
SSL = rffi.COpaquePtr('SSL')
BIO = rffi.COpaquePtr('BIO')
X509 = rffi.COpaquePtr('X509')
X509_NAME = rffi.COpaquePtr('X509_NAME')

HAVE_OPENSSL_RAND = OPENSSL_VERSION_NUMBER >= 0x0090500f

constants = {}
constants["SSL_ERROR_ZERO_RETURN"] = PY_SSL_ERROR_ZERO_RETURN
constants["SSL_ERROR_WANT_READ"] = PY_SSL_ERROR_WANT_READ
constants["SSL_ERROR_WANT_WRITE"] = PY_SSL_ERROR_WANT_WRITE
constants["SSL_ERROR_WANT_X509_LOOKUP"] = PY_SSL_ERROR_WANT_X509_LOOKUP
constants["SSL_ERROR_SYSCALL"] = PY_SSL_ERROR_SYSCALL
constants["SSL_ERROR_SSL"] = PY_SSL_ERROR_SSL
constants["SSL_ERROR_WANT_CONNECT"] = PY_SSL_ERROR_WANT_CONNECT
constants["SSL_ERROR_EOF"] = PY_SSL_ERROR_EOF
constants["SSL_ERROR_INVALID_ERROR_CODE"] = PY_SSL_ERROR_INVALID_ERROR_CODE

constants["CERT_NONE"]     = PY_SSL_CERT_NONE
constants["CERT_OPTIONAL"] = PY_SSL_CERT_OPTIONAL
constants["CERT_REQUIRED"] = PY_SSL_CERT_REQUIRED

constants["PROTOCOL_SSLv2"]  = PY_SSL_VERSION_SSL2
constants["PROTOCOL_SSLv3"]  = PY_SSL_VERSION_SSL3
constants["PROTOCOL_SSLv23"] = PY_SSL_VERSION_SSL23
constants["PROTOCOL_TLSv1"]  = PY_SSL_VERSION_TLS1

constants["OPENSSL_VERSION_NUMBER"] = OPENSSL_VERSION_NUMBER
ver = OPENSSL_VERSION_NUMBER
ver, status = divmod(ver, 16)
ver, patch  = divmod(ver, 256)
ver, fix    = divmod(ver, 256)
ver, minor  = divmod(ver, 256)
ver, major  = divmod(ver, 256)
constants["OPENSSL_VERSION_INFO"] = (major, minor, fix, patch, status)
constants["OPENSSL_VERSION"] = SSLEAY_VERSION

def external(name, argtypes, restype, **kw):
    kw['compilation_info'] = eci
    return rffi.llexternal(
        name, argtypes, restype, **kw)

def ssl_external(name, argtypes, restype, **kw):
    globals()['libssl_' + name] = external(
        name, argtypes, restype, **kw)

ssl_external('SSL_load_error_strings', [], lltype.Void)
ssl_external('SSL_library_init', [], rffi.INT)
if HAVE_OPENSSL_RAND:
    ssl_external('RAND_add', [rffi.CCHARP, rffi.INT, rffi.DOUBLE], lltype.Void)
    ssl_external('RAND_status', [], rffi.INT)
    ssl_external('RAND_egd', [rffi.CCHARP], rffi.INT)
ssl_external('SSL_CTX_new', [SSL_METHOD], SSL_CTX)
ssl_external('SSLv23_method', [], SSL_METHOD)
ssl_external('SSL_CTX_use_PrivateKey_file', [SSL_CTX, rffi.CCHARP, rffi.INT], rffi.INT)
ssl_external('SSL_CTX_use_certificate_chain_file', [SSL_CTX, rffi.CCHARP], rffi.INT)
ssl_external('SSL_CTX_ctrl', [SSL_CTX, rffi.INT, rffi.INT, rffi.VOIDP], rffi.INT)
ssl_external('SSL_CTX_set_verify', [SSL_CTX, rffi.INT, rffi.VOIDP], lltype.Void)
ssl_external('SSL_new', [SSL_CTX], SSL)
ssl_external('SSL_set_fd', [SSL, rffi.INT], rffi.INT)
ssl_external('BIO_ctrl', [BIO, rffi.INT, rffi.INT, rffi.VOIDP], rffi.INT)
ssl_external('SSL_get_rbio', [SSL], BIO)
ssl_external('SSL_get_wbio', [SSL], BIO)
ssl_external('SSL_set_connect_state', [SSL], lltype.Void)
ssl_external('SSL_connect', [SSL], rffi.INT)
ssl_external('SSL_get_error', [SSL, rffi.INT], rffi.INT)

ssl_external('ERR_get_error', [], rffi.INT)
ssl_external('ERR_error_string', [rffi.ULONG, rffi.CCHARP], rffi.CCHARP)
ssl_external('SSL_get_peer_certificate', [SSL], X509)
ssl_external('X509_get_subject_name', [X509], X509_NAME)
ssl_external('X509_get_issuer_name', [X509], X509_NAME)
ssl_external('X509_NAME_oneline', [X509_NAME, rffi.CCHARP, rffi.INT], rffi.CCHARP)
ssl_external('X509_free', [X509], lltype.Void)
ssl_external('SSL_free', [SSL], lltype.Void)
ssl_external('SSL_CTX_free', [SSL_CTX], lltype.Void)
ssl_external('SSL_write', [SSL, rffi.CCHARP, rffi.INT], rffi.INT)
ssl_external('SSL_pending', [SSL], rffi.INT)
ssl_external('SSL_read', [SSL, rffi.CCHARP, rffi.INT], rffi.INT)

ssl_external('SSL_read', [SSL, rffi.CCHARP, rffi.INT], rffi.INT)

EVP_MD_CTX = rffi.COpaquePtr('EVP_MD_CTX')
EVP_MD     = rffi.COpaquePtr('EVP_MD')

EVP_get_digestbyname = external(
    'EVP_get_digestbyname',
    [rffi.CCHARP], EVP_MD)
EVP_DigestInit = external(
    'EVP_DigestInit',
    [EVP_MD_CTX, EVP_MD], rffi.INT)
EVP_DigestUpdate = external(
    'EVP_DigestUpdate',
    [EVP_MD_CTX, rffi.CCHARP, rffi.SIZE_T], rffi.INT)

def _init_ssl():
    libssl_SSL_load_error_strings()
    libssl_SSL_library_init()

