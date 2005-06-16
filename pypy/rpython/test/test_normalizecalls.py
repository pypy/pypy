from pypy.annotation import model as annmodel
from pypy.translator.translator import Translator
from pypy.rpython.rtyper import RPythonTyper


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
