from pypy.annotation import model as annmodel
from pypy.translator.translator import Translator
from pypy.rpython.rtyper import RPythonTyper
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.lltypesystem import lltype


def rtype(fn, argtypes=[]):
    t = Translator(fn)
    t.annotate(argtypes)
    typer = RPythonTyper(t.annotator)
    typer.specialize()
    #t.view()
    t.checkgraphs()
    return t

# ____________________________________________________________

def test_normalize_f2_as_taking_string_argument():
    def f1(l1):
        pass
    def f2(l2):
        pass
    def g(n):
        if n > 0:
            f1("123")
            f = f1
        else:
            f2("b")
            f = f2
        f("a")

    translator = rtype(g, [int])
    f1graph = translator.getflowgraph(f1)
    f2graph = translator.getflowgraph(f2)
    s_l1 = translator.annotator.binding(f1graph.getargs()[0])
    s_l2 = translator.annotator.binding(f2graph.getargs()[0])
    assert s_l1.__class__ == annmodel.SomeString   # and not SomeChar
    assert s_l2.__class__ == annmodel.SomeString   # and not SomeChar
    #translator.view()

def test_normalize_keyword_call():
    def f1(a, b):
        return (a, b, 0, 0)
    def f2(b, c=123, a=456, d=789):
        return (a, b, c, d)
    def g(n):
        if n > 0:
            f = f1
        else:
            f = f2
        f(a=5, b=6)

    translator = rtype(g, [int])
    f1graph = translator.getflowgraph(f1)
    f2graph = translator.getflowgraph(f2)
    assert len(f1graph.getargs()) == 2
    assert len(f2graph.getargs()) == 2   # normalized to the common call pattern
    #translator.view()

def test_normalize_returnvar():
    def add_one(n):
        return n+1
    def add_half(n):
        return n+0.5
    def dummyfn(n, i):
        if i == 1:
            adder = add_one
        else:
            adder = add_half
        return adder(n)

    res = interpret(dummyfn, [52, 1])
    assert type(res) is float and res == 53.0
    res = interpret(dummyfn, [7, 2])
    assert type(res) is float and res == 7.5

def test_normalize_missing_return():
    def add_one(n):
        return n+1
    def oups(n):
        raise ValueError
    def dummyfn(n, i):
        if i == 1:
            adder = add_one
        else:
            adder = oups
        try:
            return adder(n)
        except ValueError:
            return -1

    translator = rtype(dummyfn, [int, int])
    add_one_graph = translator.getflowgraph(add_one)
    oups_graph    = translator.getflowgraph(oups)
    assert add_one_graph.getreturnvar().concretetype == lltype.Signed
    assert oups_graph   .getreturnvar().concretetype == lltype.Signed
    #translator.view()

def test_normalize_abstract_method():
    class Base:
        def fn(self):
            raise NotImplementedError
    class Sub1(Base):
        def fn(self):
            return 1
    class Sub2(Base):
        def fn(self):
            return 2
    def dummyfn(n):
        if n == 1:
            x = Sub1()
        else:
            x = Sub2()
        return x.fn()

    translator = rtype(dummyfn, [int])
    base_graph = translator.getflowgraph(Base.fn.im_func)
    sub1_graph = translator.getflowgraph(Sub1.fn.im_func)
    sub2_graph = translator.getflowgraph(Sub2.fn.im_func)
    assert base_graph.getreturnvar().concretetype == lltype.Signed
    assert sub1_graph.getreturnvar().concretetype == lltype.Signed
    assert sub2_graph.getreturnvar().concretetype == lltype.Signed
