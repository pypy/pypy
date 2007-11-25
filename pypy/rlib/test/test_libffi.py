
""" Tests of libffi wrappers and dl* friends
"""

from pypy.rpython.test.test_llinterp import interpret
from pypy.translator.c.test.test_genc import compile
from pypy.rlib.libffi import *
from pypy.rpython.lltypesystem.ll2ctypes import ALLOCATED
from pypy.rpython.lltypesystem import rffi, lltype
import os, sys
import py
import time

def setup_module(mod):
    if not sys.platform.startswith('linux'):
        py.test.skip("Fragile tests, linux only by now")

class TestDLOperations:
    def setup_method(self, meth):
        ALLOCATED.clear()

    def test_dlopen(self):
        py.test.raises(OSError, "dlopen(rffi.str2charp('xxxxxxxxxxxx'))")
        assert dlopen(rffi.str2charp('/lib/libc.so.6'))
        
    def get_libc(self):
        return CDLL('/lib/libc.so.6')
    
    def test_library_open(self):
        lib = self.get_libc()
        del lib
        assert not ALLOCATED

    def test_library_get_func(self):
        lib = self.get_libc()
        ptr = lib.getpointer('time', [], ffi_type_void)
        py.test.raises(KeyError, lib.getpointer, 'xxxxxxxxxxxxxxx', [], ffi_type_void)
        del ptr
        del lib
        assert len(ALLOCATED) == 1

    def test_library_func_call(self):
        lib = self.get_libc()
        ptr = lib.getpointer('rand', [], ffi_type_sint)
        zeroes = 0
        first = ptr.call(rffi.INT)
        for i in range(100):
            res = ptr.call(rffi.INT)
            if res == first:
                zeroes += 1
        assert zeroes < 90
        # not very hard check, but something :]
        del ptr
        del lib
        assert len(ALLOCATED) == 1 # ffi_type_sint get allocated

    def test_call_args(self):
        libm = CDLL('libm.so')
        pow = libm.getpointer('pow', [ffi_type_double, ffi_type_double],
                              ffi_type_double)
        pow.push_arg(2.0)
        pow.push_arg(2.0)
        res = pow.call(rffi.DOUBLE)
        assert res == 4.0
        pow.push_arg(3.0)
        pow.push_arg(3.0)
        res = pow.call(rffi.DOUBLE)
        assert res == 27.0
        del pow
        del libm
        assert len(ALLOCATED) == 1

    def test_wrong_args(self):
        libc = CDLL('libc.so.6')
        # XXX assume time_t is long
        ctime = libc.getpointer('time', [ffi_type_pointer], ffi_type_ulong)
        x = lltype.malloc(lltype.GcStruct('xxx'))
        y = lltype.malloc(lltype.GcArray(rffi.LONG), 3)
        z = lltype.malloc(lltype.Array(rffi.LONG), 4, flavor='raw')
        py.test.raises(ValueError, "ctime.push_arg(x)")
        py.test.raises(ValueError, "ctime.push_arg(y)")
        py.test.raises(ValueError, "ctime.push_arg(z)")
        del ctime
        del libc
        lltype.free(z, flavor='raw')
        # allocation check makes no sense, since we've got GcStructs around

    def test_call_time(self):
        libc = CDLL('libc.so.6')
        # XXX assume time_t is long
        ctime = libc.getpointer('time', [ffi_type_pointer], ffi_type_ulong)
        ctime.push_arg(lltype.nullptr(rffi.CArray(rffi.LONG)))
        t0 = ctime.call(rffi.LONG)
        time.sleep(2)
        ctime.push_arg(lltype.nullptr(rffi.CArray(rffi.LONG)))
        t1 = ctime.call(rffi.LONG)
        assert t1 > t0
        l_t = lltype.malloc(rffi.CArray(rffi.LONG), 1, flavor='raw')
        ctime.push_arg(l_t)
        t1 = ctime.call(rffi.LONG)
        assert l_t[0] == t1
        lltype.free(l_t, flavor='raw')
        del ctime
        assert len(ALLOCATED) == 1

    def test_compile(self):
        import py
        py.test.skip("Segfaulting test, skip")
        # XXX cannot run it on top of llinterp, some problems
        # with pointer casts

        def f(x, y):
            libm = CDLL('libm.so')
            c_pow = libm.getpointer('pow', [ffi_type_double, ffi_type_double], ffi_type_double)
            c_pow.push_arg(x)
            c_pow.push_arg(y)
            res = c_pow.call(rffi.DOUBLE)
            return res

        fn = compile(f, [float, float])
        res = fn(2.0, 4.0)
        assert res == 16.0

        
