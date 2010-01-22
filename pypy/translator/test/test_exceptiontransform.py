import py
from pypy.translator.translator import TranslationContext, graphof
from pypy.translator.simplify import join_blocks
from pypy.translator import exceptiontransform
from pypy.objspace.flow.model import summary
from pypy.rpython.test.test_llinterp import get_interpreter
from pypy.translator.backendopt.all import backend_optimizations
from pypy import conftest
import sys

def check_debug_build():
    # the 'not conftest.option.view' is because debug builds rarely
    # have pygame, so if you want to see the graphs pass --view and
    # don't be surprised when the test then passes when it shouldn't.
    if not hasattr(sys, 'gettotalrefcount') and not conftest.option.view:
        py.test.skip("test needs a debug build of Python")

_already_transformed = {}

def interpret(func, values):
    interp, graph = get_interpreter(func, values)
    t = interp.typer.annotator.translator
    if t not in _already_transformed:
        etrafo = exceptiontransform.ExceptionTransformer(t)
        etrafo.transform_completely()
        _already_transformed[t] = True
    return interp.eval_graph(graph, values)

class BaseTestExceptionTransform:
    type_system = None

    def transform_func(self, fn, inputtypes, backendopt=False):
        t = TranslationContext()
        t.buildannotator().build_types(fn, inputtypes)
        t.buildrtyper(type_system=self.type_system).specialize()
        if conftest.option.view:
            t.view()
        if backendopt:
            backend_optimizations(t)
        g = graphof(t, fn)
        etrafo = exceptiontransform.ExceptionTransformer(t)
        etrafo.create_exception_handling(g)
        join_blocks(g)
        if conftest.option.view:
            t.view()
        return t, g

    def compile(self, fn, inputargs):
        raise NotImplementedError
    
    def test_simple(self):
        def one():
            return 1

        def foo():
            one()
            return one()

        t, g = self.transform_func(foo, [])
        assert len(list(g.iterblocks())) == 2 # graph does not change 
        result = interpret(foo, [])
        assert result == 1
        f = self.compile(foo, [])
        assert f() == 1

    def test_passthrough(self):
        def one(x):
            if x:
                raise ValueError()

        def foo():
            one(0)
            one(1)
        t, g = self.transform_func(foo, [])
        f = self.compile(foo, [])
        py.test.raises(ValueError, f)

    def test_catches(self):
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
        t, g = self.transform_func(foo, [int])
        assert len(list(g.iterblocks())) == 10
        f = self.compile(foo, [int])
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

    def test_bare_except(self):
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
        t, g = self.transform_func(foo, [int])
        assert len(list(g.iterblocks())) == 6
        f = self.compile(foo, [int])
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

    def test_raises(self):
        def foo(x):
            if x:
                raise ValueError()
        t, g = self.transform_func(foo, [int])
        assert len(list(g.iterblocks())) == 3
        f = self.compile(foo, [int])
        f(0)
        py.test.raises(ValueError, f, 1)


    def test_no_multiple_transform(self):
        def f(x):
            return x + 1
        t = TranslationContext()
        t.buildannotator().build_types(f, [int])
        t.buildrtyper(type_system=self.type_system).specialize()
        g = graphof(t, f)
        etrafo = exceptiontransform.ExceptionTransformer(t)
        etrafo.create_exception_handling(g)
        etrafo2 = exceptiontransform.ExceptionTransformer(t)
        py.test.raises(AssertionError, etrafo2.create_exception_handling, g)

    def test_preserve_can_raise(self):
        def f(x):
            raise ValueError
        t = TranslationContext()
        t.buildannotator().build_types(f, [int])
        t.buildrtyper(type_system=self.type_system).specialize()
        g = graphof(t, f)
        etrafo = exceptiontransform.ExceptionTransformer(t)
        etrafo.create_exception_handling(g)    
        assert etrafo.raise_analyzer.analyze_direct_call(g)

    def test_reraise_is_not_raise(self):
        def one(x):
            if x == 1:
                raise ValueError()
            elif x == 2:
                raise TypeError()
            return x - 5
        def foo(x):
            try:
                return one(x)
            except ValueError:
                return -42
        t, g = self.transform_func(foo, [int])
        for block in g.iterblocks():
            for op in block.operations:
                # the operation 'debug_record_traceback' should only show up
                # in a normal raise, not in a reraise
                assert op.opname != 'debug_record_traceback'
        f = self.compile(foo, [int])
        result = interpret(foo, [7])
        assert result == 2
        result = f(7)
        assert result == 2
        result = interpret(foo, [1])
        assert result == -42
        result = f(1)
        assert result == -42


class TestLLType(BaseTestExceptionTransform):
    type_system = 'lltype'

    def compile(self, fn, inputargs):
        from pypy.translator.c.test.test_genc import compile
        return compile(fn, inputargs)

    def test_needs_keepalive(self):
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
        f = self.compile(foo, [int])
        res = f(0)
        assert res == 43

    def test_inserting_zeroing_op(self):
        from pypy.rpython.lltypesystem import lltype
        S = lltype.GcStruct("S", ('x', lltype.Signed))
        def f(x):
            s = lltype.malloc(S)
            s.x = 0
            return s.x
        t = TranslationContext()
        t.buildannotator().build_types(f, [int])
        t.buildrtyper(type_system=self.type_system).specialize()
        g = graphof(t, f)
        etrafo = exceptiontransform.ExceptionTransformer(t)
        etrafo.create_exception_handling(g)
        ops = dict.fromkeys([o.opname for b, o in g.iterblockops()])
        assert 'zero_gc_pointers_inside' in ops

    def test_llexternal(self):
        from pypy.rpython.lltypesystem.rffi import llexternal
        from pypy.rpython.lltypesystem import lltype
        z = llexternal('z', [lltype.Signed], lltype.Signed)
        def f(x):
            y = -1
            if x > 0:
                y = z(x)
            return y + x

        t,g = self.transform_func(f, [int], True)
        # llexternals normally should not raise, the graph should have no exception
        # checking
        assert summary(g) == {'int_gt': 1, 'int_add': 1, 'direct_call': 1}

    def test_get_exception_addr(self):
        from pypy.rpython.lltypesystem import lltype, llmemory
        from pypy.rpython.lltypesystem.lloperation import llop
        def foo():
            # a bit hard to test, really
            a = llop.get_exception_addr(llmemory.Address)
            assert lltype.typeOf(a) is llmemory.Address
            a = llop.get_exc_value_addr(llmemory.Address)
            assert lltype.typeOf(a) is llmemory.Address
            return 42
        f = self.compile(foo, [])
        res = f()
        assert res == 42


class TestOOType(BaseTestExceptionTransform):
    type_system = 'ootype'

    def compile(self, fn, inputargs):
        from pypy.translator.cli.test.runtest import compile_function
        return compile_function(fn, inputargs, auto_raise_exc=True, exctrans=True)
