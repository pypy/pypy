# "coughcoughcough" applies to most of this file

from pypy.translator.translator import TranslationContext
from pypy.jit import tl
from pypy.jit.llabstractinterp import LLAbstractInterp
from pypy.rpython.rstr import string_repr


def jit_tl(code):
    t = TranslationContext()
    t.buildannotator().build_types(tl.interp, [str, int])
    rtyper = t.buildrtyper()
    rtyper.specialize()
    graph1 = t.graphs[0] 

    interp = LLAbstractInterp()
    hints = {graph1.getargs()[0]: string_repr.convert_const(code),
             graph1.getargs()[1]: 0}

    graph2 = interp.eval(graph1, hints)
    graph2.show()


def INPROGRESS_test_jit_tl_1():
    code = tl.compile("""
        PUSH 42
    """)
    jit_tl(code)
