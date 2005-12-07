from pypy.translator.translator import TranslationContext
from pypy.rpython.annlowlevel import annotate_lowlevel_helper
from pypy.rpython.lltypesystem import lltype
from pypy.jit.llabstractinterp import LLAbstractInterp

def test_simple():
    def ll_function(x, y):
        return x + y

    t = TranslationContext()
    a = t.buildannotator()
    argtypes = [a.typeannotation(int), a.typeannotation(int)]
    graph1 = annotate_lowlevel_helper(a, ll_function, argtypes)
    t.buildrtyper().specialize()
    interp = LLAbstractInterp()
    # tell 'y=42'
    hints = {graph1.getargs()[1]: 42}
    graph2 = interp.eval(graph1, hints)
    # check that the result is "lambda x: x+42"
    assert len(graph2.startblock.operations) == 1
    assert len(graph2.getargs()) == 1
    op = graph2.startblock.operations[0]
    assert op.opname == 'int_add'
    assert op.args[0] is graph2.getargs()[0]
    assert op.args[0].concretetype == lltype.Signed
    assert op.args[1].value == 42
    assert op.args[1].concretetype == lltype.Signed
    assert len(graph2.startblock.exits) == 1
    assert graph2.startblock.exits[0].target is graph2.returnblock
