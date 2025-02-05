from rpython.rlib.rdynload import *
from rpython.rlib.clibffi import get_libc_name
from rpython.rtyper.lltypesystem import rffi, lltype
from rpython.translator.platform import platform
import py

class TestDLOperations:
    def test_dlopen(self):
        s = 'xxxxxxxxxxxx'
        py.test.raises(DLOpenError, "dlopen(s)")
        #
        s = get_libc_name()
        assert dlopen(s)

    def test_dlsym(self):
        s = get_libc_name()
        lib = dlopen(s)
        handle = rffi.cast(lltype.Ptr(lltype.FuncType([lltype.Signed],
                           lltype.Signed)), dlsym(lib, 'abs'))
        assert 1 == handle(1)
        assert 1 == handle(-1)

    def test_ldscripts(self):
        # this test only makes sense on linux
        if platform.name != "linux":
            return

        fname = os.path.join(os.path.dirname(__file__), "ldscript_working1.so")
        assert "C object" in str(dlopen(fname))

        fname = os.path.join(os.path.dirname(__file__), "ldscript_working2.so")
        assert "C object" in str(dlopen(fname))

        fname = os.path.join(os.path.dirname(__file__), "ldscript_broken1.so")
        py.test.raises(DLOpenError, 'dlopen(fname)')

        fname = os.path.join(os.path.dirname(__file__), "ldscript_broken2.so")
        py.test.raises(DLOpenError, 'dlopen(fname)')
