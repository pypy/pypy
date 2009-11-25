# XXX clean up these tests to use more uniform helpers
import py
import os
from pypy.objspace.flow.model import traverse, Block, Link, Variable, Constant
from pypy.objspace.flow.model import last_exception, checkgraph
from pypy.translator.backendopt import canraise
from pypy.translator.backendopt.inline import simple_inline_function, CannotInline
from pypy.translator.backendopt.inline import auto_inlining, Inliner
from pypy.translator.backendopt.inline import collect_called_graphs
from pypy.translator.backendopt.inline import measure_median_execution_cost
from pypy.translator.backendopt.inline import instrument_inline_candidates
from pypy.translator.backendopt.checkvirtual import check_virtual_methods
from pypy.translator.translator import TranslationContext, graphof
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.test.tool import LLRtypeMixin, OORtypeMixin
from pypy.rlib.rarithmetic import ovfcheck
from pypy.translator.test.snippet import is_perfect_number
from pypy.translator.backendopt.all import INLINE_THRESHOLD_FOR_TEST
from pypy.conftest import option
from pypy.translator.backendopt import removenoops
from pypy.objspace.flow.model import summary

def no_missing_concretetype(node):
    if isinstance(node, Block):
        for v in node.inputargs:
            assert hasattr(v, 'concretetype')
        for op in node.operations:
            for v in op.args:
                assert hasattr(v, 'concretetype')
            assert hasattr(op.result, 'concretetype')
    if isinstance(node, Link):
        if node.exitcase is not None:
            assert hasattr(node, 'llexitcase')
        for v in node.args:
            assert hasattr(v, 'concretetype')
        if isinstance(node.last_exception, (Variable, Constant)):
            assert hasattr(node.last_exception, 'concretetype')
        if isinstance(node.last_exc_value, (Variable, Constant)):
            assert hasattr(node.last_exc_value, 'concretetype')

def sanity_check(t):
    # look for missing '.concretetype'
    for graph in t.graphs:
        checkgraph(graph)
        traverse(no_missing_concretetype, graph)

class CustomError1(Exception):
    def __init__(self):
        self.data = 123

class CustomError2(Exception):
    def __init__(self):
        self.data2 = 456

class BaseTestInline:
    type_system = None

    def _skip_oo(self, reason):
        if self.type_system == 'ootype':
            py.test.skip("ootypesystem doesn't support %s, yet" % reason)

    def translate(self, func, argtypes):
        t = TranslationContext()
        t.buildannotator().build_types(func, argtypes)
        t.buildrtyper(type_system=self.type_system).specialize()
        return t

    def check_inline(self, func, in_func, sig, entry=None,
                     inline_guarded_calls=False,
                     graph=False):
        if entry is None:
            entry = in_func
        t = self.translate(entry, sig)
        # inline!
        sanity_check(t)    # also check before inlining (so we don't blame it)
        if option.view:
            t.view()
        raise_analyzer = canraise.RaiseAnalyzer(t)
        inliner = Inliner(t, graphof(t, in_func), func,
                          t.rtyper.lltype_to_classdef_mapping(),
                          inline_guarded_calls,
                          raise_analyzer=raise_analyzer)
        inliner.inline_all()
        if option.view:
            t.view()
        sanity_check(t)
        interp = LLInterpreter(t.rtyper)
        def eval_func(args):
            return interp.eval_graph(graphof(t, entry), args)
        if graph:
            return eval_func, graphof(t, func)
        return eval_func

    def check_auto_inlining(self, func, sig, multiplier=None, call_count_check=False,
                            checkvirtual=False, remove_same_as=False, heuristic=None,
                            const_fold_first=False):
        t = self.translate(func, sig)
        if checkvirtual:
            check_virtual_methods()
        if const_fold_first:
            from pypy.translator.backendopt.constfold import constant_fold_graph
            from pypy.translator.simplify import eliminate_empty_blocks
            for graph in t.graphs:
                constant_fold_graph(graph)
                eliminate_empty_blocks(graph)
        if option.view:
            t.view()
        # inline!
        sanity_check(t)    # also check before inlining (so we don't blame it)

        threshold = INLINE_THRESHOLD_FOR_TEST
        if multiplier is not None:
            threshold *= multiplier

        call_count_pred = None
        if call_count_check:
            call_count_pred = lambda lbl: True
            instrument_inline_candidates(t.graphs, threshold)

        if remove_same_as:
            for graph in t.graphs:
                removenoops.remove_same_as(graph)
            
        if heuristic is not None:
            kwargs = {"heuristic": heuristic}
        else:
            kwargs = {}
        auto_inlining(t, threshold, call_count_pred=call_count_pred, **kwargs)

        sanity_check(t)
        if option.view:
            t.view()
        interp = LLInterpreter(t.rtyper)
        def eval_func(args):
            return interp.eval_graph(graphof(t, func), args)
        return eval_func, t


    def test_inline_simple(self):
        def f(x, y):
            return (g(x, y) + 1) * x
        def g(x, y):
            if x > 0:
                return x * y
            else:
                return -x * y
        eval_func = self.check_inline(g, f, [int, int])
        result = eval_func([-1, 5])
        assert result == f(-1, 5)
        result = eval_func([2, 12])
        assert result == f(2, 12)

    def test_nothing_to_inline(self):
        def f():
            return 1
        def g():
            return 2
        eval_func = self.check_inline(g, f, [])
        assert eval_func([]) == 1

    def test_inline_big(self):
        def f(x):
            result = []
            for i in range(1, x+1):
                if is_perfect_number(i):
                    result.append(i)
            return result
        eval_func = self.check_inline(is_perfect_number, f, [int])
        result = eval_func([10])
        result = self.ll_to_list(result)
        assert len(result) == len(f(10))

    def test_inline_raising(self):
        def f(x):
            if x == 1:
                raise CustomError1
            return x
        def g(x):
            a = f(x)
            if x == 2:
                raise CustomError2
        def h(x):
            try:
                g(x)
            except CustomError1:
                return 1
            except CustomError2:
                return 2
            return x
        eval_func = self.check_inline(f,g, [int], entry=h)
        result = eval_func([0])
        assert result == 0
        result = eval_func([1])
        assert result == 1
        result = eval_func([2])
        assert result == 2    

    def test_inline_several_times(self):
        def f(x):
            return (x + 1) * 2
        def g(x):
            if x:
                a = f(x) + f(x)
            else:
                a = f(x) + 1
            return a + f(x)
        eval_func = self.check_inline(f, g, [int])
        result = eval_func([0])
        assert result == g(0)
        result = eval_func([42])
        assert result == g(42)

    def test_always_inline(self):
        def f(x, y, z, k):
            p = (((x, y), z), k)
            return p[0][0][0] + p[-1]
        f._always_inline_ = True

        def g(x, y, z, k):
            a = f(x, y, z, k)
            return a
        eval_func, t = self.check_auto_inlining(g, [int, int, int, int], multiplier=0.1)
        graph = graphof(t, g)
        s = summary(graph)
        assert len(s) > 3

    def test_inline_exceptions(self):
        customError1 = CustomError1()
        customError2 = CustomError2()
        def f(x):
            if x == 0:
                raise customError1
            if x == 1:
                raise customError2
        def g(x):
            try:
                f(x)
            except CustomError1:
                return 2
            except CustomError2:
                return x+2
            return 1
        eval_func = self.check_inline(f, g, [int])
        result = eval_func([0])
        assert result == 2
        result = eval_func([1])
        assert result == 3
        result = eval_func([42])
        assert result == 1

    def test_inline_const_exceptions(self):
        valueError = ValueError()
        keyError = KeyError()
        def f(x):
            if x == 0:
                raise valueError
            if x == 1:
                raise keyError
        def g(x):
            try:
                f(x)
            except ValueError:
                return 2
            except KeyError:
                return x+2
            return 1
        eval_func = self.check_inline(f, g, [int])
        result = eval_func([0])
        assert result == 2
        result = eval_func([1])
        assert result == 3
        result = eval_func([42])
        assert result == 1

    def test_inline_exception_guarded(self):
        def h(x):
            if x == 1:
                raise CustomError1()
            elif x == 2:
                raise CustomError2()
            return 1
        def f(x):
            try:
                return h(x)
            except:
                return 87
        def g(x):
            try:
                return f(x)
            except CustomError1:
                return 2
        eval_func = self.check_inline(f, g, [int], inline_guarded_calls=True)
        result = eval_func([0])
        assert result == 1
        result = eval_func([1])
        assert result == 87
        result = eval_func([2])
        assert result == 87

    def test_inline_with_raising_non_call_op(self):
        class A:
            pass
        def f():
            return A()
        def g():
            try:
                a = f()
            except MemoryError:
                return 1
            return 2
        py.test.raises(CannotInline, self.check_inline, f, g, [])

    def test_inline_var_exception(self):
        def f(x):
            e = None
            if x == 0:
                e = CustomError1()
            elif x == 1:
                e = KeyError()
            if x == 0 or x == 1:
                raise e
        def g(x):
            try:
                f(x)
            except CustomError1:
                return 2
            except KeyError:
                return 3
            return 1

        eval_func, _ = self.check_auto_inlining(g, [int], multiplier=10)
        result = eval_func([0])
        assert result == 2
        result = eval_func([1])
        assert result == 3
        result = eval_func([42])
        assert result == 1

    def test_inline_nonraising_into_catching(self):
        def f(x):
            return x+1
        def g(x):
            try:
                return f(x)
            except KeyError:
                return 42
        eval_func = self.check_inline(f, g, [int])
        result = eval_func([7654])
        assert result == 7655

    def DONOTtest_call_call(self):
        # for reference.  Just remove this test if we decide not to support
        # catching exceptions while inlining a graph that contains further
        # direct_calls.
        def e(x):
            if x < 0:
                raise KeyError
            return x+1
        def f(x):
            return e(x)+2
        def g(x):
            try:
                return f(x)+3
            except KeyError:
                return -1
        eval_func = self.check_inline(f, g, [int])
        result = eval_func([100])
        assert result == 106
        result = eval_func(g, [-100])
        assert result == -1

    def test_for_loop(self):
        def f(x):
            result = 0
            for i in range(0, x):
                result += i
            return result
        t = self.translate(f, [int])
        sanity_check(t)    # also check before inlining (so we don't blame it)
        for graph in t.graphs:
            if graph.name.startswith('ll_rangenext'):
                break
        else:
            assert 0, "cannot find ll_rangenext_*() function"
        simple_inline_function(t, graph, graphof(t, f))
        sanity_check(t)
        interp = LLInterpreter(t.rtyper)
        result = interp.eval_graph(graphof(t, f), [10])
        assert result == 45

    def test_inline_constructor(self):
        class A:
            def __init__(self, x, y):
                self.bounds = (x, y)
            def area(self, height=10):
                return height * (self.bounds[1] - self.bounds[0])
        def f(i):
            a = A(117, i)
            return a.area()
        eval_func = self.check_inline(A.__init__.im_func, f, [int])
        result = eval_func([120])
        assert result == 30

    def test_cannot_inline_recursive_function(self):
        def factorial(n):
            if n > 1:
                return n * factorial(n-1)
            else:
                return 1
        def f(n):
            return factorial(n//2)
        py.test.raises(CannotInline, self.check_inline, factorial, f, [int])

    def test_auto_inlining_small_call_big(self):
        def leaf(n):
            total = 0
            i = 0
            while i < n:
                total += i
                if total > 100:
                    raise OverflowError
                i += 1
            return total
        def g(n):
            return leaf(n)
        def f(n):
            try:
                return g(n)
            except OverflowError:
                return -1
        eval_func, t = self.check_auto_inlining(f, [int], multiplier=10)
        f_graph = graphof(t, f)
        assert len(collect_called_graphs(f_graph, t)) == 0

        result = eval_func([10])
        assert result == 45
        result = eval_func([15])
        assert result == -1

    def test_auto_inlining_small_call_big_call_count(self):
        def leaf(n):
            total = 0
            i = 0
            while i < n:
                total += i
                if total > 100:
                    raise OverflowError
                i += 1
            return total
        def g(n):
            return leaf(n)
        def f(n):
            try:
                return g(n)
            except OverflowError:
                return -1
        eval_func, t = self.check_auto_inlining(f, [int], multiplier=10,
                                           call_count_check=True)
        f_graph = graphof(t, f)
        assert len(collect_called_graphs(f_graph, t)) == 0

        result = eval_func([10])
        assert result == 45
        result = eval_func([15])
        assert result == -1

    def test_inline_exception_catching(self):
        def f3():
            raise CustomError1
        def f2():
            try:
                f3()
            except CustomError1:
                return True
            else:
                return False
        def f():
            return f2()
        eval_func = self.check_inline(f2, f, [])
        result = eval_func([])
        assert result is True

    def test_inline_catching_different_exception(self):
        d = {1: 2}
        def f2(n):
            try:
                return ovfcheck(n+1)
            except OverflowError:
                raise
        def f(n):
            try:
                return f2(n)
            except ValueError:
                return -1
        eval_func = self.check_inline(f2, f, [int])
        result = eval_func([54])
        assert result == 55

    def test_inline_raiseonly(self):
        c = CustomError1()
        def f2(x):
            raise c
        def f(x):
            try:
                return f2(x)
            except CustomError1:
                return 42
        eval_func = self.check_inline(f2, f, [int])
        result = eval_func([98371])
        assert result == 42

    def test_measure_median_execution_cost(self):
        def f(x):
            x += 1
            x += 1
            x += 1
            while True:
                x += 1
                x += 1
                x += 1
                if x: break
                x += 1
                x += 1
                x += 1
                x += 1
                x += 1
            x += 1
            return x
        t = TranslationContext()
        graph = t.buildflowgraph(f)
        res = measure_median_execution_cost(graph)
        assert round(res, 5) == round(32.333333333, 5)

    def test_indirect_call_with_exception(self):
        class Dummy:
            pass
        def x1():
            return Dummy()   # can raise MemoryError
        def x2():
            return None
        def x3(x):
            if x:
                f = x1
            else:
                f = x2
            return f()
        def x4():
            try:
                x3(0)
                x3(1)
            except CustomError2:
                return 0
            return 1
        assert x4() == 1
        py.test.raises(CannotInline, self.check_inline, x3, x4, [])

    def test_list_iteration(self):
        def f():
            tot = 0
            for item in [1,2,3]:
                tot += item
            return tot

        eval_func, t = self.check_auto_inlining(f, [], checkvirtual=True)
        f_graph = graphof(t, f)
        called_graphs = collect_called_graphs(f_graph, t, include_oosend=False)
        assert len(called_graphs) == 0

        result = eval_func([])
        assert result == 6

    def test_bug_in_find_exception_type(self):
        def h():
            pass
        def g(i):
            if i > 0:
                raise IndexError
            else:
                h()
        def f(i):
            try:
                g(i)
            except IndexError:
                pass

        eval_func, t = self.check_auto_inlining(f, [int], remove_same_as=True,
                                                const_fold_first=True)
        eval_func([-66])
        eval_func([282])


class TestInlineLLType(LLRtypeMixin, BaseTestInline):

    def test_correct_keepalive_placement(self):
        def h(x):
            if not x:
                raise ValueError
            return 1
        def f(x):
            s = "a %s" % (x, )
            try:
                h(len(s))
            except ValueError:
                pass
            return -42
        eval_func, t = self.check_auto_inlining(f, [int])
        res = eval_func([42])
        assert res == -42

    def test_keepalive_hard_case(self):
        from pypy.rpython.lltypesystem import lltype
        Y = lltype.Struct('y', ('n', lltype.Signed))
        X = lltype.GcStruct('x', ('y', Y))
        def g(x):
            if x:
                return 3
            else:
                return 4
        def f():
            x = lltype.malloc(X)
            x.y.n = 2
            y = x.y
            z1 = g(y.n)
            z = y.n
            return z+z1
        eval_func = self.check_inline(g, f, [])
        res = eval_func([])
        assert res == 5


class TestInlineOOType(OORtypeMixin, BaseTestInline):

    def test_rtype_r_dict_exceptions(self):
        from pypy.rlib.objectmodel import r_dict
        def raising_hash(obj):
            if obj.startswith("bla"):
                raise TypeError
            return 1
        def eq(obj1, obj2):
            return obj1 is obj2
        def f():
            d1 = r_dict(eq, raising_hash)
            d1['xxx'] = 1
            try:
                x = d1["blabla"]
            except Exception:
                return 42
            return x

        eval_func, t = self.check_auto_inlining(f, [])
        res = eval_func([])
        assert res == 42

    def test_float(self):
        ex = ['', '    ']
        def fn(i):
            s = ex[i]
            try:
                return float(s)
            except ValueError:
                return -999.0

        eval_func, t = self.check_auto_inlining(fn, [int])
        expected = fn(0)
        res = eval_func([0])
        assert res == expected

    def test_oosend(self):
        class A:
            def foo(self, x):
                return x
        def fn(x):
            a = A()
            return a.foo(x)

        eval_func, t = self.check_auto_inlining(fn, [int], checkvirtual=True)
        expected = fn(42)
        res = eval_func([42])
        assert res == expected

    def test_not_inline_oosend(self):
        class A:
            def foo(self, x):
                return x
        class B(A):
            def foo(self, x):
                return x+1

        def fn(flag, x):
            if flag:
                obj = A()
            else:
                obj = B()
            return obj.foo(x)

        eval_func, t = self.check_auto_inlining(fn, [bool, int], checkvirtual=True)
        expected = fn(True, 42)
        res = eval_func([True, 42])
        assert res == expected

    def test_oosend_inherited(self):
        class BaseStringFormatter:
            def __init__(self):
                self.fmtpos = 0
            def forward(self):
                self.fmtpos += 1

        class StringFormatter(BaseStringFormatter):
            def __init__(self, fmt):
                BaseStringFormatter.__init__(self)
                self.fmt = fmt
            def peekchr(self):
                return self.fmt[self.fmtpos]
            def peel_num(self):
                while True:
                    self.forward()
                    c = self.peekchr()
                    if self.fmtpos == 2: break
                return 0

        class UnicodeStringFormatter(BaseStringFormatter):
            pass
        
        def fn(x):
            if x:
                fmt = StringFormatter('foo')
                return fmt.peel_num()
            else:
                dummy = UnicodeStringFormatter()
                dummy.forward()
                return 0

        eval_func, t = self.check_auto_inlining(fn, [int], checkvirtual=True,
                                                remove_same_as=True)
        expected = fn(1)
        res = eval_func([1])
        assert res == expected

    def test_classattr(self):
        class A:
            attr = 666
        class B(A):
            attr = 42
        def fn5():
            b = B()
            return b.attr

        eval_func, t = self.check_auto_inlining(fn5, [], checkvirtual=True)
        res = eval_func([])
        assert res == 42

    def test_indirect_call_becomes_direct(self):
        def h1(n):
            return n+1
        def h2(n):
            return n+2
        def g(myfunc, n):
            return myfunc(n*5)
        def f(x, y):
            return g(h1, x) + g(h2, y)
        eval_func = self.check_inline(g, f, [int, int])
        res = eval_func([10, 173])
        assert res == f(10, 173)
