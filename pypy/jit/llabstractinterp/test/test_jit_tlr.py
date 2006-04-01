from pypy.annotation import model as annmodel
from pypy.annotation.listdef import ListDef
from pypy.translator.translator import TranslationContext
from pypy.jit.llabstractinterp.llabstractinterp import LLAbstractInterp
from pypy.jit.llabstractinterp.test.test_llabstractinterp import summary
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.rstr import string_repr

from pypy.jit.tl import tlr


def test_compile():
    t = TranslationContext()
    t.buildannotator().build_types(tlr.interpret, [str, int])
    rtyper = t.buildrtyper()
    rtyper.specialize()

    interp = LLAbstractInterp()
    hints = {0: string_repr.convert_const(tlr.SQUARE)}
    graph2 = interp.eval(t.graphs[0], hints)
    #graph2.show()

    llinterp = LLInterpreter(rtyper)
    res = llinterp.eval_graph(graph2, [17])
    assert res == 289

    insns = summary(graph2)
    assert insns == {'int_add': 2,
                     'int_is_true': 1}
