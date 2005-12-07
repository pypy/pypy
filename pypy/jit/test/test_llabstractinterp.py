from pypy.translator.translator import TranslationContext
from pypy.rpython.annlowlevel import annotate_lowlevel_helper
from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython import rstr
from pypy.annotation import model as annmodel
from pypy.jit.llabstractinterp import LLAbstractInterp


def annotation(a, x):
    T = lltype.typeOf(x)
    if T == lltype.Ptr(rstr.STR):
        t = str
    else:
        t = annmodel.lltype_to_annotation(T)
    return a.typeannotation(t)

def abstrinterp(ll_function, argvalues, arghints):
    t = TranslationContext()
    a = t.buildannotator()
    argtypes = [annotation(a, value) for value in argvalues]
    graph1 = annotate_lowlevel_helper(a, ll_function, argtypes)
    rtyper = t.buildrtyper()
    rtyper.specialize()
    interp = LLAbstractInterp()
    hints = {}
    argvalues2 = argvalues[:]
    lst = list(arghints)
    lst.sort()
    lst.reverse()
    for hint in lst:
        hints[graph1.getargs()[hint]] = argvalues2[hint]
        del argvalues2[hint]
    graph2 = interp.eval(graph1, hints)
    # check the result by running it
    llinterp = LLInterpreter(rtyper)
    result1 = llinterp.eval_graph(graph1, argvalues)
    result2 = llinterp.eval_graph(graph2, argvalues2)
    assert result1 == result2
    # return a summary of the instructions left in graph2
    insns = {}
    for block in graph2.iterblocks():
        for op in block.operations:
            insns[op.opname] = insns.get(op.opname, 0) + 1
    return graph2, insns


def test_simple():
    def ll_function(x, y):
        return x + y

    graph2, insns = abstrinterp(ll_function, [6, 42], [1])
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

def test_simple2():
    def ll_function(x, y):
        return x + y
    graph2, insns = abstrinterp(ll_function, [6, 42], [0, 1])
    assert not insns

def test_constantbranch():
    def ll_function(x, y):
        if x:
            y += 1
        y += 2
        return y
    graph2, insns = abstrinterp(ll_function, [6, 42], [0])
    assert insns == {'int_add': 2}

def test_constantbranch_two_constants():
    def ll_function(x, y):
        if x:
            y += 1
        y += 2
        return y
    graph2, insns = abstrinterp(ll_function, [6, 42], [0, 1])
    assert not insns

def test_branch():
    def ll_function(x, y):
        if x:
            y += 1
        y += 2
        return y
    graph2, insns = abstrinterp(ll_function, [6, 42], [])
    assert insns == {'int_is_true': 1, 'int_add': 2}
