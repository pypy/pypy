import py
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.backendopt.test.test_malloc import check_malloc_removed
from pypy.translator.translator import Translator
from pypy.objspace.flow.model import Constant
from pypy.rpython.llinterp import LLInterpreter


class A:
    def __init__(self, x, y):
        self.bounds = (x, y)
    def mean(self, percentage=50):
        x, y = self.bounds
        total = x*percentage + y*(100-percentage)
        return total//100

def condition(n):
    return n >= 100

def firstthat(function, condition):
    for n in range(101):
        if condition(function(n)):
            return n
    else:
        return -1

def myfunction(n):
    a = A(117, n)
    return a.mean()

def big():
    """This example should be turned into a simple 'while' loop with no
    malloc nor direct_call by back-end optimizations, given a high enough
    inlining threshold.
    """
    return firstthat(myfunction, condition)


def test_big():
    assert big() == 83

    t = Translator(big)
    t.annotate([])
    t.specialize()
    backend_optimizations(t, inline_threshold=100)

    graph = t.getflowgraph()
    check_malloc_removed(graph)

    interp = LLInterpreter(t.flowgraphs, t.rtyper)
    res = interp.eval_function(big, [])
    assert res == 83
