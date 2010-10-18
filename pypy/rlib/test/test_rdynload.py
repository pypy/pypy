from pypy.rlib.rdynload import *
from pypy.rlib.clibffi import get_libc_name
from pypy.rpython.lltypesystem import rffi, lltype
import py

class TestDLOperations:
    def test_dlopen(self):
        py.test.raises(DLOpenError, "dlopen(rffi.str2charp('xxxxxxxxxxxx'))")
        assert dlopen(rffi.str2charp(get_libc_name()))

    def test_dlsym(self):
        lib = dlopen(rffi.str2charp(get_libc_name()))
        handle = rffi.cast(lltype.Ptr(lltype.FuncType([lltype.Signed],
                           lltype.Signed)), dlsym(lib, 'abs'))
        assert 1 == handle(1)
        assert 1 == handle(-1)
