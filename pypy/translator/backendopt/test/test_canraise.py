from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.backendopt.canraise import RaiseAnalyzer
from pypy.conftest import option

def translate(func, sig):
    t = TranslationContext()
    t.buildannotator().build_types(func, sig)
    t.buildrtyper().specialize()
    if option.view:
        t.view()
    return t, RaiseAnalyzer(t)

def test_can_raise_simple():
    def g(x):
        return True

    def f(x):
        return g(x - 1)
    t, ra = translate(f, [int])
    fgraph = graphof(t, f)
    result = ra.can_raise(fgraph.startblock.operations[0])
    assert not result

def test_can_raise_recursive():
    def g(x):
        return f(x)

    def f(x):
        if x:
            return g(x - 1)
        return 1
    t, ra = translate(f, [int])
    ggraph = graphof(t, g)
    result = ra.can_raise(ggraph.startblock.operations[1])
    assert result # due to stack check every recursive function can raise

def test_can_raise_exception():
    def g():
        raise ValueError
    def f():
        return g()
    t, ra = translate(f, [])
    fgraph = graphof(t, f)
    result = ra.can_raise(fgraph.startblock.operations[0])
    assert result

def test_indirect_call():
    def g1():
        raise ValueError
    def g2():
        return 2
    def f(x):
        if x:
            g = g1
        else:
            g = g2
        return g()
    def h(x):
        return f(x)
    t, ra = translate(h, [int])
    hgraph = graphof(t, h)
    result = ra.can_raise(hgraph.startblock.operations[0])
    assert result

def test_external():
    import os.path
    def f(x):
        return os.path.isdir(str(x))
    t, ra = translate(f, [int])
    fgraph = graphof(t, f)
    result = ra.can_raise(fgraph.startblock.operations[0])
    assert result

def test_instantiate():
    from pypy.rpython.objectmodel import instantiate
    class A:
        pass 
    class B(A):
        pass
    def g(x):
        if x:
            C = A
        else:
            C = B
        a = instantiate(C)
    def f(x):
        return g(x)
    t, ra = translate(f, [int])
    fgraph = graphof(t, f)
    result = ra.can_raise(fgraph.startblock.operations[0])
    assert result
