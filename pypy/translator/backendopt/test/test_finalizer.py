
import py
from pypy.translator.backendopt.finalizer import FinalizerAnalyzer
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.all import backend_optimizations
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.conftest import option


class BaseFinalizerAnalyzerTests(object):
    """ Below are typical destructors that we encounter in pypy
    """

    type_system = None
    
    def analyze(self, func, sig, func_to_analyze=None, backendopt=False):
        if func_to_analyze is None:
            func_to_analyze = func
        t = TranslationContext()
        t.buildannotator().build_types(func, sig)
        t.buildrtyper(type_system=self.type_system).specialize()
        if backendopt:
            backend_optimizations(t)
        if option.view:
            t.view()
        a = FinalizerAnalyzer(t)
        fgraph = graphof(t, func_to_analyze)
        result = a.analyze_direct_call(fgraph)
        return result

    def test_nothing(self):
        def f():
            pass
        r = self.analyze(f, [])
        assert not r


class TestLLType(BaseFinalizerAnalyzerTests):
    type_system = 'lltype'

    def test_malloc(self):
        S = lltype.GcStruct('S')
        
        def f():
            return lltype.malloc(S)

        r = self.analyze(f, [])
        assert r

    def test_raw_free_getfield(self):
        S = lltype.Struct('S')
        
        class A(object):
            def __init__(self):
                self.x = lltype.malloc(S, flavor='raw')

            def __del__(self):
                if self.x:
                    self.x = lltype.nullptr(S)
                    lltype.free(self.x, flavor='raw')

        def f():
            return A()

        r = self.analyze(f, [], A.__del__.im_func)
        assert not r

    def test_c_call(self):
        C = rffi.CArray(lltype.Signed)
        c = rffi.llexternal('x', [lltype.Ptr(C)], lltype.Signed)

        def g():
            p = lltype.malloc(C, 3, flavor='raw')
            f(p)
        
        def f(p):
            c(rffi.ptradd(p, 0))
            lltype.free(p, flavor='raw')

        r = self.analyze(g, [], f, backendopt=True)
        assert not r

    def test_chain(self):
        class B(object):
            def __init__(self):
                self.counter = 1
        
        class A(object):
            def __init__(self):
                self.x = B()

            def __del__(self):
                self.x.counter += 1

        def f():
            A()

        r = self.analyze(f, [], A.__del__.im_func)
        assert r

    def test_os_call(self):
        py.test.skip("can allocate OSError, but also can raise, ignore for now")
        import os
        
        def f(i):
            os.close(i)

        r = self.analyze(f, [int], backendopt=True)
        assert not r

class TestOOType(BaseFinalizerAnalyzerTests):
    type_system = 'ootype'
