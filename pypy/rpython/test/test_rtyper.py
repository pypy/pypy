from pypy.annotation import model as annmodel
from pypy.translator.translator import Translator
from pypy.rpython.lltype import *
from pypy.rpython.test.test_llinterp import interpret 
from pypy.rpython.rtyper import RPythonTyper
import py

def setup_module(mod): 
    mod.logstate = py.log._getstate()
    py.log.setconsumer("rtyper", py.log.STDOUT)
    py.log.setconsumer("annrpython", None)   

def teardown_module(mod): 
    py.log._setstate(mod.logstate) 

def test_reprkey_dont_clash():
    stup1 = annmodel.SomeTuple((annmodel.SomeFloat(), 
                                annmodel.SomeInteger()))
    stup2 = annmodel.SomeTuple((annmodel.SomeString(), 
                                annmodel.SomeInteger()))
    key1 = stup1.rtyper_makekey()
    key2 = stup2.rtyper_makekey()
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
    t = Translator(f)
    t.annotate([int])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
    graph = t.getflowgraph(f)
    assert graph.getreturnvar().concretetype == Signed
    assert graph.startblock.exits[0].args[0].concretetype == Signed

def test_retval_None():
    def f(x):
        pass
    t = Translator(f)
    t.annotate([int])
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
    graph = t.getflowgraph(f)
    assert graph.getreturnvar().concretetype == Void
    assert graph.startblock.exits[0].args[0].concretetype == Void

def test_ll_calling_ll():
    import test_llann
    tst = test_llann.TestLowLevelAnnotateTestCase()
    a, vTs = tst.test_ll_calling_ll()
    a.translator.specialize()
    assert [vT.concretetype for vT in vTs] == [Void] * 4

def test_ll_calling_ll2():
    import test_llann
    tst = test_llann.TestLowLevelAnnotateTestCase()
    a, vTs = tst.test_ll_calling_ll2()
    a.translator.specialize()
    assert [vT.concretetype for vT in vTs] == [Void] * 3
    
