import py
import sys
try:
    import cffi
except ImportError:
    py.test.skip('cffi required')

from rpython.rlib import rvmprof
srcdir = py.path.local(rvmprof.__file__).join("..", "src")


@py.test.mark.skipif("sys.platform == 'win32'")
class TestDirect(object):
    def setup_class(clz):
        ffi = cffi.FFI()
        ffi.cdef("""
        int vmp_dyn_register_jit_page(intptr_t addr, intptr_t end_addr, const char * name);
        int vmp_dyn_cancel(int ref);
        """)

        with open(str(srcdir.join("shared/vmp_dynamic.c"))) as fd:
            ffi.set_source("rpython.rlib.rvmprof.test._test_dynamic", fd.read(),
                    include_dirs=[str(srcdir.join('shared'))],
                    libraries=['unwind'])

        ffi.compile(verbose=True)

        from rpython.rlib.rvmprof.test import _test_dynamic
        clz.lib = _test_dynamic.lib
        clz.ffi = _test_dynamic.ffi

    def test_register_dynamic_code(self):
        lib = self.lib
        ffi = self.ffi

        assert 1 == lib.vmp_dyn_cancel(100)
        assert 1 == lib.vmp_dyn_cancel(0)
        assert 1 == lib.vmp_dyn_cancel(-1)

        s = ffi.new("char[]", "hello jit compiler")
        assert 0 == lib.vmp_dyn_register_jit_page(0x100, 0x200, ffi.NULL)
        assert 1 == lib.vmp_dyn_register_jit_page(0x200, 0x300, s)

        lib.vmp_dyn_cancel(0)
        lib.vmp_dyn_cancel(1)


