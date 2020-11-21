import py
from rpython.translator.translator import TranslationContext, graphof
from rpython.translator.simplify import join_blocks
from rpython.translator import exceptiontransform
from rpython.flowspace.model import summary
from rpython.rtyper.llinterp import LLException
from rpython.rtyper.test.test_llinterp import get_interpreter
from rpython.translator.backendopt.all import backend_optimizations
from rpython.conftest import option
import sys

def check_debug_build():
    # the 'not option.view' is because debug builds rarely
    # have pygame, so if you want to see the graphs pass --view and
    # don't be surprised when the test then passes when it shouldn't.
    if not hasattr(sys, 'gettotalrefcount') and not option.view:
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

class TestExceptionTransform:
    def compile(self, fn, inputargs, **kwargs):
        from rpython.translator.c.test.test_genc import compile
        return compile(fn, inputargs, **kwargs)

    def transform_func(self, fn, inputtypes, backendopt=False):
        t = TranslationContext()
        t.buildannotator().build_types(fn, inputtypes)
        t.buildrtyper().specialize()
        if option.view:
            t.view()
        if backendopt:
            backend_optimizations(t)
        g = graphof(t, fn)
        etrafo = exceptiontransform.ExceptionTransformer(t)
        etrafo.create_exception_handling(g)
        join_blocks(g)
        if option.view:
            t.view()
        return t, g

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
        f(expected_exception_name='ValueError')

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
        f(1, expected_exception_name='ValueError')


    def test_no_multiple_transform(self):
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

    def test_preserve_can_raise(self):
        def f(x):
            raise ValueError
        t = TranslationContext()
        t.buildannotator().build_types(f, [int])
        t.buildrtyper().specialize()
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

    def test_needs_keepalive(self):
        check_debug_build()
        from rpython.rtyper.lltypesystem import lltype
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
        from rpython.rtyper.lltypesystem import lltype
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

    def test_llexternal(self):
        from rpython.rtyper.lltypesystem.rffi import llexternal
        from rpython.rtyper.lltypesystem import lltype
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
        from rpython.rtyper.lltypesystem import lltype, llmemory
        from rpython.rtyper.lltypesystem.lloperation import llop
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

    def test_default_error_value(self):
        def foo(x):
            if x == 42:
                raise ValueError
            return 123

        result = interpret(foo, [1])
        assert result == 123
        with py.test.raises(LLException) as exc:
            interpret(foo, [42])
        assert exc.value.error_value == -1
        assert 'ValueError' in str(exc.value)

    def test_custom_error_value(self):
        from rpython.rlib.objectmodel import ll_error_value
        @ll_error_value(-456)
        def foo(x):
            if x == 42:
                raise ValueError
            return x

        result = interpret(foo, [123])
        assert result == 123
        with py.test.raises(LLException) as exc:
            interpret(foo, [42])
        assert exc.value.error_value == -456
        assert 'ValueError' in str(exc.value)
        #
        compiled_foo = self.compile(foo, [int], backendopt=False)
        assert compiled_foo(123) == 123
        compiled_foo(42, expected_exception_name='ValueError')

    def test_custom_error_value_propagate(self):
        from rpython.rlib.objectmodel import ll_error_value
        @ll_error_value(-456)
        def foo(x):
            if x == 42:
                raise ValueError
            return x

        def bar(x):
            try:
                return foo(x)
            except ValueError:
                return 123

        result = interpret(bar, [10])
        assert result == 10
        result = interpret(bar, [42])
        assert result == 123
        #
        compiled_bar = self.compile(bar, [int], backendopt=False)
        assert compiled_bar(10) == 10
        assert compiled_bar(42) == 123

    def test_custom_error_value_reraise(self):
        from rpython.rlib.objectmodel import ll_error_value
        @ll_error_value(-456)
        def foo(x):
            if x == 42:
                raise ValueError
            return x

        def bar(x):
            try:
                return foo(x)
            except ValueError:
                raise

        with py.test.raises(LLException) as exc:
            interpret(bar, [42])
        assert exc.value.error_value == -1

    def test_raise_from_llhelper(self):
        from rpython.rtyper.lltypesystem import lltype
        from rpython.rtyper.annlowlevel import llhelper

        def fn(a, b):
            if b == 0:
                raise ZeroDivisionError
            return a/b

        FN = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
        def h(a, b):
            fnptr = llhelper(FN, fn)
            try:
                return fnptr(a, b)
            except ZeroDivisionError:
                return -a

        compiled_h = self.compile(h, [int, int])
        res = compiled_h(39, 3)
        assert res == 13
        res = compiled_h(39, 0)
        assert res == -39

    def test_propagate_from_llhelper(self):
        from rpython.rtyper.lltypesystem import lltype
        from rpython.rtyper.annlowlevel import llhelper

        def fn(a, b):
            if b == 0:
                raise ZeroDivisionError
            return a/b

        FN = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
        def h(a, b):
            fnptr = llhelper(FN, fn)
            try:
                return fnptr(a, b)
            except ZeroDivisionError:
                return -a

        compiled_h = self.compile(h, [int, int])
        res = compiled_h(39, 3)
        assert res == 13
        res = compiled_h(39, 0)
        assert res == -39

    def test_llhelper_can_raise_custome_error_value(self):
        from rpython.rtyper.lltypesystem import lltype
        from rpython.rtyper.annlowlevel import llhelper
        from rpython.rlib.objectmodel import llhelper_can_raise

        @llhelper_can_raise(error_value=-123)
        def fn(a, b):
            if b == 0:
                raise ZeroDivisionError
            return a/b

        # check that if we call it directly, it returns -123
        with py.test.raises(LLException) as exc:
            interpret(fn, [3, 0])
        assert exc.value.error_value == -123


        # ==============
        # XXX this test is BROKEN at the moment, DO NOT MERGE THIS BRANCH
        #
        # The problem is that the return types of h and fnptr are both Signed:
        # so, exceptiontransform creates a graph which directly return the
        # value of fnptr, EVEN IN CASE OF EXCEPTION. But in this case, h
        # should return -1, not -123.
        #
        # If you do "return float(fntptr(a, b))" the test passes, because in
        # this case exceptiontransform have to put an explit
        # "has-an-rpy-exc-occurred" check after the indirect call
        # ==============

        # check that we can call it as a llhelper
        FN = lltype.Ptr(lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed))
        def h(a, b):
            fnptr = llhelper(FN, fn)
            return fnptr(a, b)

        with py.test.raises(LLException) as exc:
            interpret(h, [3, 0])
        assert exc.value.error_value == -1 # the return value of h, not of fn!
