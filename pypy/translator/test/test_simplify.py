from pypy.translator.translator import Translator
from pypy.objspace.flow.model import traverse, Block

def test_remove_direct_call_without_side_effects():
    def f(x):
        return x + 123
    def g(x):
        a = f(x)
        return x * 12
    t = Translator(g)
    a = t.annotate([int])
    t.specialize()
    t.backend_optimizations()
    assert len(t.flowgraphs[g].startblock.operations) == 1

def test_dont_remove_external_calls():
    import os
    def f(x):
        os.close(x)
    t = Translator(f)
    a = t.annotate([int])
    t.specialize()
    t.backend_optimizations()
    assert len(t.flowgraphs[f].startblock.operations) == 1

def test_remove_recursive_call():
    def rec(a):
        if a <= 1:
            return 0
        else:
            return rec(a - 1) + 1
    def f(x):
        a = rec(x)
        return x + 12
    t = Translator(f)
    a = t.annotate([int])
    t.specialize()
    t.backend_optimizations()
    assert len(t.flowgraphs[f].startblock.operations)

def test_dont_remove_if_exception_guarded():
    def f(x):
        a = {} #do some stuff to prevent inlining
        a['123'] = 123
        a['1123'] = 1234
        return x + 1
    def g(x):
        try:
            a = f(x)
        except OverflowError:
            raise
        else:
            return 1
    t = Translator(g)
    a = t.annotate([int])
    t.specialize()
    t.backend_optimizations()
    assert t.flowgraphs[g].startblock.operations[-1].opname == 'direct_call'

