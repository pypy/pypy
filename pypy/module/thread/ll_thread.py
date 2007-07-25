
from pypy.rpython.lltypesystem import rffi
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.lltypesystem.rffi import platform
from pypy.rpython.extfunc import genericcallable
from pypy.module.thread.os_thread import Bootstrapper
from pypy.translator.tool.cbuild import cache_c_module
import thread, py


class ThreadError(Exception):
    def __init__(self, msg):
        self.msg = msg

class Lock(object):
    """ Container for low-level implementation
    of a lock object
    """
    def __init__(self, ll_lock):
        self._lock = ll_lock

includes = ['unistd.h', 'thread.h']

def setup_thread_so():
    from pypy.tool.autopath import pypydir
    pypydir = py.path.local(pypydir)
    srcdir = pypydir.join('translator', 'c', 'src')
    modname = '_thread'
    files = [srcdir.join('thread.c')]
    cache_c_module(files, modname, include_dirs=[str(srcdir)])
    return str(pypydir.join('_cache', modname)) + '.so'
libraries = [setup_thread_so()]

def llexternal(name, args, result):
    return rffi.llexternal(name, args, result, includes=includes,
                           libraries=libraries)

c_thread_start = llexternal('RPyThreadStart', [lltype.FuncType([rffi.VOIDP],
                            rffi.VOIDP)], rffi.INT)

TLOCKP = rffi.COpaque('struct RPyOpaque_ThreadLock', includes=includes)

c_thread_lock_init = llexternal('RPyThreadLockInit', [TLOCKP], lltype.Void)
c_thread_acuirelock = llexternal('RPyThreadAcquireLock', [TLOCKP, rffi.INT],
                                 rffi.INT)
c_thread_releaselock = llexternal('RPyThreadReleaseLock', [TLOCKP], lltype.Void)

def ll_allocate_lock():
    ll_lock = lltype.malloc(TLOCKP.TO, flavor='raw')
    res = c_thread_lock_init(ll_lock)
    if res == -1:
        raise ThreadError("out of resources")
    return Lock(ll_lock)

def ll_acquire_lock(lock, waitflag):
    return c_thread_acuirelock(lock._lock, waitflag)

def ll_release_lock(lock):
    try:
        if ll_acquire_lock(lock, 0):
            raise ThreadError("bad lock")
    finally:
        c_thread_releaselock(lock._lock)

    
