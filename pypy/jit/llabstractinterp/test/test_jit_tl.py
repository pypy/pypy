# "coughcoughcough" applies to most of this file

import py
from pypy.translator.translator import TranslationContext
from pypy.jit.tl import tl
from pypy.jit.llabstractinterp.llabstractinterp import LLAbstractInterp
from pypy.rpython.rstr import string_repr
from pypy.rpython.llinterp import LLInterpreter
from pypy.jit.llabstractinterp.test.test_llabstractinterp import summary
#from pypy.translator.backendopt import inline

#py.test.skip("in-progress")

def setup_module(mod):
    t = TranslationContext()
    t.buildannotator().build_types(tl.interp, [str, int])
    rtyper = t.buildrtyper()
    rtyper.specialize()
    #inline.auto_inlining(t, 0.3)
    
    mod.graph1 = t.graphs[0]
    mod.llinterp = LLInterpreter(rtyper)
    

def jit_tl(code):
    interp = LLAbstractInterp()
    hints = {0: string_repr.convert_const(code),
             1: 0}
    graph2 = interp.eval(graph1, hints)

    result1 = llinterp.eval_graph(graph1, [string_repr.convert_const(code), 0])
    result2 = llinterp.eval_graph(graph2, [])

    assert result1 == result2

    #interp.graphs[0].show()

    # return a summary of the instructions left in graph2
    return summary(graph2)


def run_jit(code):
    code = tl.compile(code)
    return jit_tl(code)


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
            ROLL -2   # at the moment we see a potential IndexError here
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

def test_factorial():
    insns = run_jit('''
            PUSH 1   #  accumulator
            PUSH 7   #  N

        start:
            PICK 0
            PUSH 1
            LE
            BR_COND exit

            SWAP
            PICK 1
            MUL
            SWAP
            PUSH 1
            SUB
            PUSH 1
            BR_COND start

        exit:
            POP
            RETURN
    ''')
    # currently, the condition is turned from the bool to an int and back
    # so ignore that
    if 'cast_bool_to_int' in insns:
        assert insns['cast_bool_to_int'] == 1
        assert insns['int_is_true'] == 1
        del insns['cast_bool_to_int']
        del insns['int_is_true']
    assert insns == {'int_le': 1, 'int_mul': 1, 'int_sub': 1}

def test_factorial_harder():
    insns = run_jit('''
            PUSH 1   #  accumulator
            PUSH 7   #  N

        start:
            PICK 0
            PUSH 1
            LE
            PUSH exit
            BR_COND_STK

            SWAP
            PICK 1
            MUL
            SWAP
            PUSH 1
            SUB
            PUSH 1
            BR_COND start

        exit:
            NOP      # BR_COND_STK skips this instruction
            POP
            RETURN
    ''')
    # currently, the condition is turned from the bool to an int and back
    # so ignore that
    if 'cast_bool_to_int' in insns:
        assert insns['cast_bool_to_int'] == 1
        assert insns['int_is_true'] == 1
        del insns['cast_bool_to_int']
        del insns['int_is_true']
    assert insns == {'int_le': 1, 'int_mul': 1, 'int_sub': 1}
