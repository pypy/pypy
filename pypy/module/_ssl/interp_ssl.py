from pypy.rpython.rctypes.tool import ctypes_platform
from pypy.rpython.rctypes.tool.libc import libc
import pypy.rpython.rctypes.implementation # this defines rctypes magic
from pypy.rpython.rctypes.aerrno import geterrno
from pypy.interpreter.error import OperationError
from pypy.interpreter.baseobjspace import W_Root, ObjSpace
from ctypes import *
import ctypes.util
import sys
import socket

c_void = None
libssl = cdll.LoadLibrary(ctypes.util.find_library("ssl"))

class CConfig:
    _header_ = """
    #include <openssl/opensslv.h>
    """
    OPENSSL_VERSION_NUMBER = ctypes_platform.ConstantInteger(
        "OPENSSL_VERSION_NUMBER")

class cConfig:
    pass

cConfig.__dict__.update(ctypes_platform.configure(CConfig))

OPENSSL_VERSION_NUMBER = cConfig.OPENSSL_VERSION_NUMBER

## user defined constants
HAVE_OPENSSL_RAND = OPENSSL_VERSION_NUMBER >= 0x0090500fL

X509_NAME_MAXLEN = 256
# these mirror ssl.h
PY_SSL_ERROR_NONE, PY_SSL_ERROR_SSL = 0, 1
PY_SSL_ERROR_WANT_READ, PY_SSL_ERROR_WANT_WRITE = 2, 3
PY_SSL_ERROR_WANT_X509_LOOKUP = 4
PY_SSL_ERROR_SYSCALL = 5 # look at error stack/return value/errno
PY_SSL_ERROR_ZERO_RETURN, PY_SSL_ERROR_WANT_CONNECT = 6, 7
# start of non ssl.h errorcodes
PY_SSL_ERROR_EOF = 8 # special case of SSL_ERROR_SYSCALL
PY_SSL_ERROR_INVALID_ERROR_CODE = 9

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

libssl.SSL_load_error_strings.restype = c_void
libssl.SSL_library_init.restype = c_int

def _get_error_msg():
    errno = geterrno()
    return libc.strerror(errno)

def _get_module_object(space, obj_name):
    w_module = space.getbuiltinmodule('_ssl')
    w_obj = space.getattr(w_module, space.wrap(obj_name))
    return w_obj
    
def _init_ssl():
    libssl.SSL_load_error_strings()
    libssl.SSL_library_init()
    
    # XXX: socket.sslerror = socket.error

def ssl(space):
    pass
