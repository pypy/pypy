import py
from pypy.translator.translator import TranslationContext
from pypy.jit.llabstractinterp import LLAbstractInterp, Policy
from pypy.jit.test.test_llabstractinterp import summary
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

    return graph2, summary(interp)


def test_newlist():
    py.test.skip("in-progress")
    def fn(n):
        lst = [5] * n
        return len(lst)
    graph2, insns = run(fn, [12])
    assert insns == {}
