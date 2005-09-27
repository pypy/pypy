from pypy.objspace.flow.model import traverse, Block, Link, Variable, Constant
from pypy.translator.backendopt.removezerobytemalloc import remove_zero_byte_mallocs
from pypy.translator.translator import Translator
from pypy.rpython.llinterp import LLInterpreter
from pypy.translator.test.snippet import is_perfect_number

def test_removezerobytemalloc():
    x = ()
    def func2(q):
        return q
    def zerobytemalloc():
        y = func2(x)
        return len(x)
    t = Translator(zerobytemalloc)
    a = t.annotate([])
    t.specialize()
    remove_zero_byte_mallocs(t.flowgraphs[zerobytemalloc])
    #t.view()
    lli = LLInterpreter(t.flowgraphs, t.rtyper)
    res = lli.eval_function(zerobytemalloc, ())
    assert res == 0
