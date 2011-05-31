from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rlib.jit import JitDriver, dont_look_inside
from pypy.config.translationoption import DEFL_GC

from pypy.jit.backend.x86.test.test_zrpy_gc import get_entry, get_g
from pypy.jit.backend.x86.test.test_zrpy_gc import compile_and_run
from pypy.jit.backend.x86.test.test_zrpy_gc import check


class ReleaseGILTests(object):
    def test_close_stack(self):
        from pypy.rlib.libffi import CDLL, types, ArgChain, clibffi
        from pypy.rpython.lltypesystem.ll2ctypes import libc_name
        from pypy.rpython.annlowlevel import llhelper
        from pypy.jit.metainterp.optimizeopt import ALL_OPTS_NAMES
        #
        class Glob(object):
            pass
        glob = Glob()
        class X(object):
            pass
        #
        def callback(p1, p2):
            for i in range(100):
                glob.lst.append(X())
            return rffi.cast(rffi.INT, 1)
        CALLBACK = lltype.Ptr(lltype.FuncType([lltype.Signed,
                                               lltype.Signed], rffi.INT))
        #
        @dont_look_inside
        def alloc1():
            return llmemory.raw_malloc(16)
        @dont_look_inside
        def free1(p):
            llmemory.raw_free(p)
        #
        def f42():
            length = len(glob.lst)
            c_qsort = glob.c_qsort
            raw = alloc1()
            fn = llhelper(CALLBACK, rffi._make_wrapper_for(CALLBACK, callback))
            argchain = ArgChain()
            argchain = argchain.arg(rffi.cast(lltype.Signed, raw))
            argchain = argchain.arg(rffi.cast(rffi.SIZE_T, 2))
            argchain = argchain.arg(rffi.cast(rffi.SIZE_T, 8))
            argchain = argchain.arg(rffi.cast(lltype.Signed, fn))
            c_qsort.call(argchain, lltype.Void)
            free1(raw)
            check(len(glob.lst) > length)
            del glob.lst[:]
        #
        def before():
            libc = CDLL(libc_name)
            types_size_t = clibffi.cast_type_to_ffitype(rffi.SIZE_T)
            c_qsort = libc.getpointer('qsort', [types.pointer, types_size_t,
                                                types_size_t, types.pointer],
                                      types.void)
            glob.c_qsort = c_qsort
            glob.lst = []
        #
        myjitdriver = JitDriver(greens=[], reds=['n'])
        def main(n, x):
            before()
            while n > 0:
                myjitdriver.jit_merge_point(n=n)
                f42()
                n -= 1
        #
        res = compile_and_run(get_entry(get_g(main)), DEFL_GC,
                              gcrootfinder=self.gcrootfinder, jit=True,
                              enable_opts=ALL_OPTS_NAMES,
                              thread=True)
        assert int(res) == 20

class TestGILShadowStack(ReleaseGILTests):
    gcrootfinder = "shadowstack"

class TestGILAsmGcc(ReleaseGILTests):
    gcrootfinder = "asmgcc"
