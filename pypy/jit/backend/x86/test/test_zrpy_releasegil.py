from pypy.rpython.lltypesystem import lltype, llmemory, rffi
from pypy.rlib.jit import dont_look_inside
from pypy.jit.metainterp.optimizeopt import ALL_OPTS_NAMES

from pypy.rlib.libffi import CDLL, types, ArgChain, clibffi
from pypy.rpython.lltypesystem.ll2ctypes import libc_name
from pypy.rpython.annlowlevel import llhelper

from pypy.jit.backend.x86.test.test_zrpy_gc import BaseFrameworkTests
from pypy.jit.backend.x86.test.test_zrpy_gc import check


class ReleaseGILTests(BaseFrameworkTests):
    compile_kwds = dict(enable_opts=ALL_OPTS_NAMES, thread=True)

    def define_simple(self):
        class Glob:
            pass
        glob = Glob()
        #
        def f42(n):
            c_strchr = glob.c_strchr
            raw = rffi.str2charp("foobar" + chr((n & 63) + 32))
            argchain = ArgChain()
            argchain = argchain.arg(rffi.cast(lltype.Signed, raw))
            argchain = argchain.arg(rffi.cast(rffi.INT, ord('b')))
            res = c_strchr.call(argchain, rffi.CCHARP)
            check(rffi.charp2str(res) == "bar" + chr((n & 63) + 32))
            rffi.free_charp(raw)
        #
        def before(n, x):
            libc = CDLL(libc_name)
            c_strchr = libc.getpointer('strchr', [types.pointer, types.sint],
                                       types.pointer)
            glob.c_strchr = c_strchr
            return (n, None, None, None, None, None,
                    None, None, None, None, None, None)
        #
        def f(n, x, *args):
            f42(n)
            n -= 1
            return (n, x) + args
        return before, f, None

    def test_simple(self):
        self.run('simple')

    def define_close_stack(self):
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
        def before(n, x):
            libc = CDLL(libc_name)
            types_size_t = clibffi.cast_type_to_ffitype(rffi.SIZE_T)
            c_qsort = libc.getpointer('qsort', [types.pointer, types_size_t,
                                                types_size_t, types.pointer],
                                      types.void)
            glob.c_qsort = c_qsort
            glob.lst = []
            return (n, None, None, None, None, None,
                    None, None, None, None, None, None)
        #
        def f(n, x, *args):
            f42()
            n -= 1
            return (n, x) + args
        return before, f, None

    def test_close_stack(self):
        self.run('close_stack')


class TestShadowStack(ReleaseGILTests):
    gcrootfinder = "shadowstack"

class TestAsmGcc(ReleaseGILTests):
    gcrootfinder = "asmgcc"
