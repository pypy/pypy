from rpython.rtyper.lltypesystem import lltype, llmemory, rffi
from rpython.rlib.jit import dont_look_inside
from rpython.rlib.objectmodel import invoke_around_extcall
from rpython.jit.metainterp.optimizeopt import ALL_OPTS_NAMES

from rpython.rtyper.annlowlevel import llhelper

from rpython.jit.backend.llsupport.test.zrpy_gc_test import BaseFrameworkTests
from rpython.jit.backend.llsupport.test.zrpy_gc_test import check
from rpython.tool.udir import udir


class ReleaseGILTests(BaseFrameworkTests):
    compile_kwds = dict(enable_opts=ALL_OPTS_NAMES, thread=True)

    def define_simple(self):
        class Glob:
            def __init__(self):
                self.event = 0
        glob = Glob()
        #

        c_strchr = rffi.llexternal('strchr', [rffi.CCHARP, lltype.Signed],
                                   rffi.CCHARP)

        def func():
            glob.event += 1

        def before(n, x):
            invoke_around_extcall(func, None)
            return (n, None, None, None, None, None,
                    None, None, None, None, None, None)
        #
        def f(n, x, *args):
            a = rffi.str2charp(str(n))
            c_strchr(a, ord('0'))
            lltype.free(a, flavor='raw')
            n -= 1
            return (n, x) + args
        return before, f, None

    def test_simple(self):
        self.run('simple')
        assert 'call_release_gil' in udir.join('TestCompileFramework.log').read()

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

        c_qsort = rffi.llexternal('qsort', [rffi.VOIDP, rffi.SIZE_T,
                                            rffi.SIZE_T, CALLBACK], lltype.Void)
        #
        def f42(n):
            length = len(glob.lst)
            raw = alloc1()
            fn = llhelper(CALLBACK, rffi._make_wrapper_for(CALLBACK, callback))
            if n & 1:    # to create a loop and a bridge, and also
                pass     # to run the qsort() call in the blackhole interp
            c_qsort(rffi.cast(rffi.VOIDP, raw), rffi.cast(rffi.SIZE_T, 2),
                    rffi.cast(rffi.SIZE_T, 8), fn)
            free1(raw)
            check(len(glob.lst) > length)
            del glob.lst[:]
        #
        def before(n, x):
            glob.lst = []
            
            return (n, None, None, None, None, None,
                    None, None, None, None, None, None)
        #
        def f(n, x, *args):
            f42(n)
            n -= 1
            return (n, x) + args
        return before, f, None

    def test_close_stack(self):
        self.run('close_stack')
        assert 'call_release_gil' in udir.join('TestCompileFramework.log').read()
