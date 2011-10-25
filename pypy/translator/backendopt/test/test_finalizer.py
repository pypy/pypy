
import py
from pypy.translator.backendopt.finalizer import FinalizerAnalyzer,\
     FinalizerError
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.unsimplify import varoftype
from pypy.rpython.lltypesystem import lltype, rffi
from pypy.conftest import option
from pypy.rlib import rgc


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
        result = a.analyze_light_finalizer(fgraph)
        return result

    def test_nothing(self):
        def f():
            pass
        r = self.analyze(f, [])
        assert not r

def test_various_ops():
    from pypy.objspace.flow.model import SpaceOperation, Constant

    X = lltype.Ptr(lltype.GcStruct('X'))
    Z = lltype.Ptr(lltype.Struct('Z'))
    S = lltype.GcStruct('S', ('x', lltype.Signed),
                        ('y', X),
                        ('z', Z))
    v1 = varoftype(lltype.Bool)
    v2 = varoftype(lltype.Signed)
    f = FinalizerAnalyzer(None)
    r = f.analyze(SpaceOperation('cast_int_to_bool', [v2],
                                                       v1))
    assert not r
    v1 = varoftype(lltype.Ptr(S))
    v2 = varoftype(lltype.Signed)
    v3 = varoftype(X)
    v4 = varoftype(Z)
    assert not f.analyze(SpaceOperation('bare_setfield', [v1, Constant('x'),
                                                          v2], None))
    assert     f.analyze(SpaceOperation('bare_setfield', [v1, Constant('y'),
                                                          v3], None))
    assert not f.analyze(SpaceOperation('bare_setfield', [v1, Constant('z'),
                                                          v4], None))
    
        
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

    def test_is_light_finalizer_decorator(self):
        S = lltype.GcStruct('S')

        @rgc.is_light_finalizer
        def f():
            lltype.malloc(S)
        @rgc.is_light_finalizer
        def g():
            pass
        self.analyze(g, []) # did not explode
        py.test.raises(FinalizerError, self.analyze, f, [])

class TestOOType(BaseFinalizerAnalyzerTests):
    type_system = 'ootype'
