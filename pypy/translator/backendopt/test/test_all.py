import py
from pypy.translator.backendopt.all import backend_optimizations
from pypy.translator.backendopt.support import md5digest
from pypy.translator.backendopt.test.test_malloc import check_malloc_removed
from pypy.translator.translator import TranslationContext, graphof
from pypy.objspace.flow.model import Constant
from pypy.annotation import model as annmodel
from pypy.rpython.llinterp import LLInterpreter

def translateopt(func, sig, **optflags):
    t = TranslationContext()
    t.buildannotator().build_types(func, sig)
    t.buildrtyper().specialize()
    backend_optimizations(t, **optflags)
    return t

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

    t = translateopt(big, [], inline_threshold=100, mallocs=True) 

    big_graph = graphof(t, big)
    check_malloc_removed(big_graph)

    interp = LLInterpreter(t.rtyper)
    res = interp.eval_graph(big_graph, [])
    assert res == 83


def test_for_loop():
    def f(n):
        total = 0
        for i in range(n):
            total += i
        return total

    t  = translateopt(f, [int], inline_threshold=1, mallocs=True)
    # this also checks that the BASE_INLINE_THRESHOLD is enough for 'for' loops

    f_graph = graph = graphof(t, f)
    check_malloc_removed(f_graph)

    interp = LLInterpreter(t.rtyper)
    res = interp.eval_graph(f_graph, [11])
    assert res == 55


def test_list_comp():
    def f(n1, n2):
        c = [i for i in range(n2)]
        return 33

    t  = translateopt(f, [int, int], inline_threshold=10, mallocs=True)

    f_graph = graphof(t, f)
    check_malloc_removed(f_graph)

    interp = LLInterpreter(t.rtyper)
    res = interp.eval_graph(f_graph, [11, 22])
    assert res == 33


def test_premature_death():
    import os
    from pypy.annotation.listdef import s_list_of_strings

    inputtypes = [s_list_of_strings]

    def debug(msg): 
        os.write(2, "debug: " + msg + '\n')

    def entry_point(argv):
        #debug("entry point starting") 
        for arg in argv: 
            #debug(" argv -> " + arg)
            r = arg.replace('_', '-')
            #debug(' replaced -> ' + r)
            a = r.lower()
            #debug(" lowered -> " + a)
        return 0

    t  = translateopt(entry_point, inputtypes, inline_threshold=1, mallocs=True)

    entry_point_graph = graphof(t, entry_point)

    argv = t.rtyper.getrepr(inputtypes[0]).convert_const(['./pypy-c'])

    interp = LLInterpreter(t.rtyper)
    interp.eval_graph(entry_point_graph, [argv])


def test_idempotent():
    def s(x):
        res = 0
        i = 1
        while i <= x:
            res += i
            i += 1
        return res

    def g(x):
        return s(100) + s(1) + x 

    def idempotent(n1, n2):
        c = [i for i in range(n2)]
        return 33 + big() + g(10)

    t  = translateopt(idempotent, [int, int], raisingop2direct_call_all=True)
    digest1 = md5digest(t)

    digest2 = md5digest(t)
    assert digest1 == digest2

    #XXX Inlining is currently non-idempotent.
    #    Maybe it just renames variables but it changes the graph in some way.
    backend_optimizations(t, raisingop2direct_call_all=True, inline_threshold=0)
    digest3 = md5digest(t)
    assert digest1 == digest3


def test_bug_inlined_if():
    def f(x, flag):
        if flag:
            y = x
        else:
            y = x+1
        return y*5
    def myfunc(x):
        return f(x, False) - f(x, True)

    assert myfunc(10) == 5

    t = translateopt(myfunc, [int], inline_threshold=100)
    interp = LLInterpreter(t.rtyper)
    res = interp.eval_graph(graphof(t, myfunc), [10])
    assert res == 5
