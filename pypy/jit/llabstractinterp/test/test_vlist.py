import py
from pypy.translator.translator import TranslationContext
from pypy.jit.llabstractinterp.llabstractinterp import LLAbstractInterp, Policy
from pypy.jit.llabstractinterp.test.test_llabstractinterp import summary
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.rstr import string_repr
from pypy.rpython.objectmodel import hint

policy = Policy(inlining=True, const_propagate=True, concrete_args=False,
                oopspec=True)

def run(fn, argvalues):
    t = TranslationContext()
    t.buildannotator().build_types(fn, [type(x) for x in argvalues])
    rtyper = t.buildrtyper()
    rtyper.specialize()
    graph1 = t.graphs[0]

    interp = LLAbstractInterp(policy)
    hints = {}
    llvalues = []
    for i, value in enumerate(argvalues):
        if isinstance(value, str):
            value = string_repr.convert_const(value)
        llvalues.append(value)
        hints[i] = value
    graph2 = interp.eval(graph1, hints)
    #graph2.show()

    llinterp = LLInterpreter(rtyper)
    result1 = llinterp.eval_graph(graph1, llvalues)
    result2 = llinterp.eval_graph(graph2, [])

    assert result1 == result2

    return graph2, summary(graph2)

def test_fixed_newlistfill_force():
    def fn(n):
        lst = [5] * n
        hint(lst, nonvirtual=True)
    graph2, insns = run(fn, [12])
    assert insns == {'direct_call': 13}

def test_newlistfill_force():
    def fn(n):
        lst = [5] * n
        if n < 0:
            lst.append(6)
        hint(lst, nonvirtual=True)
    graph2, insns = run(fn, [12])
    assert insns == {'direct_call': 13}

def test_newlist_force():
    def fn(n):
        lst = []
        lst.append(n)
        lst.append(5)
        lst.append(12)
        lst.pop()
        hint(lst, nonvirtual=True)
    graph2, insns = run(fn, [12])
    assert insns == {'direct_call': 3}

def test_simple_purely_virtual():
    def fn(n):
        return len([5]*n)
    graph2, insns = run(fn, [12])
    assert insns == {}

def test_copy():
    def fn(n):
        lst = []
        lst.append(n)
        lst.append(n)
        return len(list(lst))
    graph2, insns = run(fn, [12])
    assert insns == {}

def test_is_true():
    def fn(n):
        lst = [5] * n
        if lst:
            return 654
        else:
            return 321
    graph2, insns = run(fn, [12])
    assert insns == {}

def test_concat():
    def fn(n):
        lst1 = [2, 3]
        lst2 = [4] * n
        return len(lst1 + lst2)
    graph2, insns = run(fn, [12])
    assert insns == {}
