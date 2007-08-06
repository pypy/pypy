import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.simplify import join_blocks
from pypy.translator import exceptiontransform
from pypy.translator.c import genc, gc
from pypy.objspace.flow.model import c_last_exception
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.translator.c.test.test_genc import compile
from pypy import conftest
import sys

def check_debug_build():
    # the 'not conftest.option.view' is because debug builds rarely
    # have pygame, so if you want to see the graphs pass --view and
    # don't be surprised when the test then passes when it shouldn't.
    if not hasattr(sys, 'gettotalrefcount') and not conftest.option.view:
        py.test.skip("test needs a debug build of Python")

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
    f = compile(foo, [])
    assert f() == 1
    
def test_passthrough():
    def one(x):
        if x:
            raise ValueError()

    def foo():
        one(0)
        one(1)
    t, g = transform_func(foo, [])
    f = compile(foo, [])
    py.test.raises(ValueError, f)

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
    f = compile(foo, [int])
    result = interpret(foo, [6])
    assert result == 2
    result = f(6)
    assert result == 2
    result = interpret(foo, [7])
    assert result == 4
    result = f(7)
    assert result == 4
    result = interpret(foo, [8])
    assert result == 2
    result = f(8)
    assert result == 2

def test_bare_except():
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
        except:
            return 1 + x
        return 4 + x
    t, g = transform_func(foo, [int])
    assert len(list(g.iterblocks())) == 5
    f = compile(foo, [int])
    result = interpret(foo, [6])
    assert result == 2
    result = f(6)
    assert result == 2
    result = interpret(foo, [7])
    assert result == 3
    result = f(7)
    assert result == 3
    result = interpret(foo, [8])
    assert result == 2
    result = f(8)
    assert result == 2
    
def test_raises():
    def foo(x):
        if x:
            raise ValueError()
    t, g = transform_func(foo, [int])
    assert len(list(g.iterblocks())) == 3
    f = compile(foo, [int])
    f(0)
    py.test.raises(ValueError, f, 1)

def test_needs_keepalive():
    check_debug_build()
    from pypy.rpython.lltypesystem import lltype
    X = lltype.GcStruct("X",
                        ('y', lltype.Struct("Y", ('z', lltype.Signed))))
    def can_raise(n):
        if n:
            raise Exception
        else:
            return 1
    def foo(n):
        x = lltype.malloc(X)
        y = x.y
        y.z = 42
        r = can_raise(n)
        return r + y.z
    f = compile(foo, [int])
    res = f(0)
    assert res == 43

def test_no_multiple_transform():
    def f(x):
        return x + 1
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    g = graphof(t, f)
    etrafo = exceptiontransform.ExceptionTransformer(t)
    etrafo.create_exception_handling(g)
    etrafo2 = exceptiontransform.ExceptionTransformer(t)
    py.test.raises(AssertionError, etrafo2.create_exception_handling, g)

def test_preserve_can_raise():
    def f(x):
        raise ValueError
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    g = graphof(t, f)
    etrafo = exceptiontransform.ExceptionTransformer(t)
    etrafo.create_exception_handling(g)    
    assert etrafo.raise_analyzer.analyze_direct_call(g)

def test_inserting_zeroing_op():
    from pypy.rpython.lltypesystem import lltype
    S = lltype.GcStruct("S", ('x', lltype.Signed))
    def f(x):
        s = lltype.malloc(S)
        s.x = 0
        return s.x
    t = TranslationContext()
    t.buildannotator().build_types(f, [int])
    t.buildrtyper().specialize()
    g = graphof(t, f)
    etrafo = exceptiontransform.ExceptionTransformer(t)
    etrafo.create_exception_handling(g)
    ops = dict.fromkeys([o.opname for b, o in g.iterblockops()])
    assert 'zero_gc_pointers_inside' in ops
