from pypy.objspace.flow.model import traverse, Block, Link, Variable, Constant
from pypy.translator.backendopt.tailrecursion import remove_tail_calls_to_self
from pypy.translator.translator import Translator
from pypy.rpython.llinterp import LLInterpreter
from pypy.translator.test.snippet import is_perfect_number

def test_recursive_gcd():
    def gcd(a, b):
        if a == 1 or a == 0:
            return b
        if a > b:
            return gcd(b, a)
        return gcd(b % a, a)
    t = Translator(gcd)
    a = t.annotate([int, int])
    t.specialize()
    remove_tail_calls_to_self(t, t.flowgraphs[gcd])
    lli = LLInterpreter(t.flowgraphs, t.rtyper)
    res = lli.eval_function(gcd, (15, 25))
    assert res == 5
