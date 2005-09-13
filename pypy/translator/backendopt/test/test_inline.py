import py
from pypy.translator.backendopt.inline import inline_function, CannotInline
from pypy.translator.backendopt.inline import auto_inlining
from pypy.translator.backendopt.inline import collect_called_functions
from pypy.translator.translator import Translator
from pypy.rpython.llinterp import LLInterpreter
from pypy.translator.test.snippet import is_perfect_number

def test_inline_simple():
    def f(x, y):
        return (g(x, y) + 1) * x
    def g(x, y):
        if x > 0:
            return x * y
        else:
            return -x * y
    t = Translator(f)
    a = t.annotate([int, int])
    a.simplify()
    t.specialize()
    inline_function(t, g, t.flowgraphs[f])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(f, [-1, 5])
    assert result == f(-1, 5)
    result = interp.eval_function(f, [2, 12])
    assert result == f(2, 12)

def test_inline_big():
    def f(x):
        result = []
        for i in range(1, x+1):
            if is_perfect_number(i):
                result.append(i)
        return result
    t = Translator(f)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, is_perfect_number, t.flowgraphs[f])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(f, [10])
    assert result.length == len(f(10))

def test_inline_raising():
    def f(x):
        if x == 1:
            raise ValueError
        return x
    def g(x):
        a = f(x)
        if x == 2:
            raise KeyError
    def h(x):
        try:
            g(x)
        except ValueError:
            return 1
        except KeyError:
            return 2
        return x
    t = Translator(h)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, f, t.flowgraphs[g])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(h, [0])
    assert result == 0
    result = interp.eval_function(h, [1])
    assert result == 1
    result = interp.eval_function(h, [2])
    assert result == 2    

def test_inline_several_times():
    def f(x):
        return (x + 1) * 2
    def g(x):
        if x:
            a = f(x) + f(x)
        else:
            a = f(x) + 1
        return a + f(x)
    t = Translator(g)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, f, t.flowgraphs[g])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(g, [0])
    assert result == g(0)
    result = interp.eval_function(g, [42])
    assert result == g(42)

def test_inline_exceptions():
    def f(x):
        if x == 0:
            raise ValueError
        if x == 1:
            raise KeyError
    def g(x):
        try:
            f(x)
        except ValueError:
            return 2
        except KeyError:
            return x+2
        return 1
    t = Translator(g)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, f, t.flowgraphs[g])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(g, [0])
    assert result == 2
    result = interp.eval_function(g, [1])
    assert result == 3
    result = interp.eval_function(g, [42])
    assert result == 1

def DONOTtest_inline_var_exception():
    # this test is disabled for now, because f() contains a direct_call
    # (at the end, to a ll helper, to get the type of the exception object)
    def f(x):
        e = None
        if x == 0:
            e = ValueError()
        elif x == 1:
            e = KeyError()
        if x == 0 or x == 1:
            raise e
    def g(x):
        try:
            f(x)
        except ValueError:
            return 2
        except KeyError:
            return 3
        return 1
    t = Translator(g)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, f, t.flowgraphs[g])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(g, [0])
    assert result == 2
    result = interp.eval_function(g, [1])
    assert result == 3
    result = interp.eval_function(g, [42])
    assert result == 1

def DONOTtest_call_call():
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
    t = Translator(g)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, f, t.flowgraphs[g])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(g, [100])
    assert result == 106
    result = interp.eval_function(g, [-100])
    assert result == -1

def test_for_loop():
    def f(x):
        result = 0
        for i in range(0, x):
            result += i
        return result
    t = Translator(f)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    for graph in t.flowgraphs.values():
        if graph.name.startswith('ll_rangenext'):
            break
    else:
        assert 0, "cannot find ll_rangenext_*() function"
    inline_function(t, graph, t.flowgraphs[f])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(f, [10])
    assert result == 45

def test_inline_constructor():
    class A:
        def __init__(self, x, y):
            self.bounds = (x, y)
        def area(self, height=10):
            return height * (self.bounds[1] - self.bounds[0])
    def f(i):
        a = A(117, i)
        return a.area()
    t = Translator(f)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    inline_function(t, A.__init__.im_func, t.flowgraphs[f])
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(f, [120])
    assert result == 30

def test_cannot_inline_recursive_function():
    def factorial(n):
        if n > 1:
            return n * factorial(n-1)
        else:
            return 1
    def f(n):
        return factorial(n//2)
    t = Translator(f)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    py.test.raises(CannotInline,
                   "inline_function(t, factorial, t.flowgraphs[f])")

def test_auto_inlining_small_call_big():
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
    t = Translator(f)
    a = t.annotate([int])
    a.simplify()
    t.specialize()
    auto_inlining(t, threshold=10)
    assert len(collect_called_functions(t.getflowgraph(f))) == 0
    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    result = interp.eval_function(f, [10])
    assert result == 45
    result = interp.eval_function(f, [15])
    assert result == -1
