# "coughcoughcough" applies to most of this file

import py
from pypy.translator.translator import TranslationContext
from pypy.jit import tl
from pypy.jit.llabstractinterp import LLAbstractInterp
from pypy.rpython.rstr import string_repr
from pypy.rpython.llinterp import LLInterpreter
from pypy.translator.backendopt import inline

#py.test.skip("in-progress")

def entry_point(code, pc):
    # indirection needed, because the hints are not about *all* calls to
    # interp()
    return tl.interp(code, pc)

def setup_module(mod):
    t = TranslationContext()
    t.buildannotator().build_types(entry_point, [str, int])
    rtyper = t.buildrtyper()
    rtyper.specialize()
    inline.auto_inlining(t, 0.3)
    
    mod.graph1 = t.graphs[0]
    mod.llinterp = LLInterpreter(rtyper)
    

def jit_tl(code):
    interp = LLAbstractInterp()
    hints = {graph1.getargs()[0]: string_repr.convert_const(code),
             graph1.getargs()[1]: 0}
    graph2 = interp.eval(graph1, hints)

    result1 = llinterp.eval_graph(graph1, [string_repr.convert_const(code), 0])
    result2 = llinterp.eval_graph(graph2, [])

    assert result1 == result2

    #interp.graphs[1].show()     # graphs[0] should be the entry_point


def run_jit(code):
    code = tl.compile(code)
    jit_tl(code)


def test_simple1():
    run_jit(''' PUSH 42
    ''')

def test_simple2():
    run_jit(''' PUSH 6
                PUSH 7
                ADD
    ''')

def test_branches():
    run_jit('''
        main:
            PUSH 0
            PUSH 1
            BR_COND somename
        label1:
            PUSH -1
            PUSH 3
            BR_COND end
        somename:   ;
            PUSH 2  //
            BR_COND label1//
        end:// should return 3
    ''')

def test_exceptions():
    run_jit('''
            PUSH 42
            PUSH -42
            ROT 2   # at the moment we see a potential IndexError here
    ''')

def test_calls():
    run_jit('''
            PUSH 1
            CALL func1
            PUSH 3
            CALL func2
            RETURN

        func1:
            PUSH 2
            RETURN  # comment

        func2:
            PUSH 4   ;comment
            PUSH 5
            ADD
            RETURN
   ''')
