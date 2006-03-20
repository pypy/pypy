from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.simplify import join_blocks
from pypy.translator.c import exceptiontransform
from pypy.objspace.flow.model import c_last_exception
from pypy.rpython.test.test_llinterp import get_interpreter

from pypy import conftest

def transform_func(fn, inputtypes):
    t = TranslationContext()
    t.buildannotator().build_types(fn, inputtypes)
    t.buildrtyper().specialize()
    if conftest.option.view:
        t.view()
    g = graphof(t, fn)
    etrafo = exceptiontransform.ExceptionTransformer(t)
    etrafo.create_exception_handling(g)
    join_blocks(g)
    if conftest.option.view:
        t.view()
    return t, g

_already_transformed = {}

def interpret(func, values):
    interp, graph = get_interpreter(func, values)
    t = interp.typer.annotator.translator
    if t not in _already_transformed:
        etrafo = exceptiontransform.ExceptionTransformer(t)
        etrafo.transform_completely()
        _already_transformed[t] = True
    return interp.eval_graph(graph, values)
 
def test_simple():
    def one():
        return 1
    
    def foo():
        one()
        return one()

    t, g = transform_func(foo, [])
    assert len(list(g.iterblocks())) == 2 # graph does not change 
    result = interpret(foo, [])
    assert result == 1
    
def test_passthrough():
    def one(x):
        if x:
            raise ValueError()

    def foo():
        one(0)
        one(1)
    t, g = transform_func(foo, [])
    assert len(list(g.iterblocks())) == 4

def test_catches():
    def one(x):
        if x == 1:
            raise ValueError()
        elif x == 2:
            raise TypeError()
        return x - 5

    def foo(x):
        x = one(x)
        try:
            x = one(x)
        except ValueError:
            return 1 + x
        except TypeError:
            return 2 + x
        except:
            return 3 + x
        return 4 + x
    t, g = transform_func(foo, [int])
    assert len(list(g.iterblocks())) == 9
    result = interpret(foo, [6])
    assert result == 2
    result = interpret(foo, [7])
    assert result == 4
    result = interpret(foo, [8])
    assert result == 2


def test_raises():
    def foo(x):
        if x:
            raise ValueError()
    t, g = transform_func(foo, [int])
    assert len(list(g.iterblocks())) == 4
   

