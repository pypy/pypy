from pypy.annotation import model as annmodel
from pypy.objspace.flow.model import Constant
from pypy.translator.translator import TranslationContext, graphof
from pypy.annotation import annrpython
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.test.test_llinterp import interpret 
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython import rmodel
import py


def setup_module(mod): 
    mod.logstate = py.log._getstate()
    py.log.setconsumer("rtyper", py.log.STDOUT)
    py.log.setconsumer("annrpython", None)   

def teardown_module(mod): 
    py.log._setstate(mod.logstate) 

def test_reprkeys_dont_clash():
    stup1 = annmodel.SomeTuple((annmodel.SomeFloat(), 
                                annmodel.SomeInteger()))
    stup2 = annmodel.SomeTuple((annmodel.SomeString(), 
                                annmodel.SomeInteger()))
    rtyper = RPythonTyper(annrpython.RPythonAnnotator(None))
    key1 = rtyper.makekey(stup1)
    key2 = rtyper.makekey(stup2)
    assert key1 != key2

def test_simple():
    def dummyfn(x):
        return x+1

    res = interpret(dummyfn, [7])
    assert res == 8

def test_function_call():
    def g(x, y):
        return x-y
    def f(x):
        return g(1, x)

    res = interpret(f, [4])
    assert res == -3 

def test_retval():
    def f(x):
        return x
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    #t.view()
    t.checkgraphs()
    graph = graphof(t, f)
    assert graph.getreturnvar().concretetype == Signed
    assert graph.startblock.exits[0].args[0].concretetype == Signed

def test_retval_None():
    def f(x):
        pass
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    #t.view()
    t.checkgraphs()
    graph = graphof(t, f)
    assert graph.getreturnvar().concretetype == Void
    assert graph.startblock.exits[0].args[0].concretetype == Void

def test_ll_calling_ll():
    import test_llann
    tst = test_llann.TestLowLevelAnnotateTestCase()
    a, vTs = tst.test_ll_calling_ll()
    rt = RPythonTyper(a)
    rt.specialize()
    assert [vT.concretetype for vT in vTs] == [Void] * 4

def test_ll_calling_ll2():
    import test_llann
    tst = test_llann.TestLowLevelAnnotateTestCase()
    a, vTs = tst.test_ll_calling_ll2()
    rt = RPythonTyper(a)
    rt.specialize()
    assert [vT.concretetype for vT in vTs] == [Void] * 3
    

def test_getgcflavor():
    class A:
        pass
    class B:
        _alloc_flavor_ = "gc"
    class R:
        _alloc_flavor_ = "raw"

    NDF = object()

    class DummyClsDescDef:
        def __init__(self, cls):
            self._cls = cls
            self.classdesc = self
            self.basedef = None

        def getmro(self):
            return [self]

        def read_attribute(self, attr, default=NDF):
            try:
                return Constant(getattr(self._cls, attr))
            except AttributeError:
                if default is NDF:
                    raise
                else:
                    return default
            
    assert rmodel.getgcflavor(DummyClsDescDef(A)) == 'gc'
    assert rmodel.getgcflavor(DummyClsDescDef(B)) == 'gc'
    assert rmodel.getgcflavor(DummyClsDescDef(R)) == 'raw'

def test_missing_gvflavor_bug():
    class MyClass:
        def set_x(self):
            self.x = create_tuple()
    def create_tuple():
        return MyClass(), 42
    def fn():
        obj = MyClass()
        obj.set_x()
        create_tuple()
    t = TranslationContext()
    t.buildannotator().build_types(fn, [])
    t.buildrtyper(type_system='ootype').specialize()
    #t.view()
    t.checkgraphs()
    graph = graphof(t, fn)
    assert graph.getreturnvar().concretetype == Void
