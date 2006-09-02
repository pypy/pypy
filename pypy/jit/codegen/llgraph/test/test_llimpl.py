from pypy.jit.codegen.llgraph.llimpl import *
from pypy.rpython.lltypesystem.lltype import *
from pypy.rpython.test.test_llinterp import interpret
from pypy.rpython.module.support import from_opaque_object
from pypy.objspace.flow import model as flowmodel

F1 = FuncType([Signed], Signed)

def build_square():
    """def square(v0): return v0*v0"""
    block = newblock()
    v0 = geninputarg(block, constTYPE(Signed))
    v1 = genop(block, 'int_mul', [v0, v0], constTYPE(Signed))
    link = closeblock1(block)
    closereturnlink(link, v1)
    return block

def test_square():
    block = build_square()
    res = runblock(block, F1, [17])
    assert res == 289

def test_rtype_newblock():
    def emptyblock():
        return newblock()
    blockcontainer = interpret(emptyblock, [])
    block = from_opaque_object(blockcontainer.obj)
    assert isinstance(block, flowmodel.Block)

def test_rtype_geninputarg():
    def onearg():
        block = newblock()
        v0 = geninputarg(block, constTYPE(Signed))
        return v0
    opaquev = interpret(onearg, [])
    v = from_opaque_object(opaquev)
    assert isinstance(v, flowmodel.Variable)
    
def test_rtype_build_square():
    blockcontainer = interpret(build_square, [])
    res = runblock(blockcontainer, F1, [17])
    assert res == 289

def build_if():
    """
    def f(v0):
        if v0 < 0:
            return 0
        else:
            return v0
    """
    block = newblock()
    v0 = geninputarg(block, constTYPE(Signed))
    const0 = genconst(0)
    v1 = genop(block, 'int_lt', [v0, const0], constTYPE(Bool))
    false_link, true_link = closeblock2(block, v1)
    closereturnlink(true_link, const0)
    closereturnlink(false_link, v0)
    return block

def test_if():
    block = build_if()
    res = runblock(block, F1, [-1])
    assert res == 0
    res = runblock(block, F1, [42])
    assert res == 42

def test_rtype_build_if():
    blockcontainer = interpret(build_if, [])
    res = runblock(blockcontainer, F1, [-1])
    assert res == 0
    res = runblock(blockcontainer, F1, [42])
    assert res == 42

def build_loop():
    """
    def f(v0):
        i = 1
        result = 1
        while i <= v0:
            result *= i
            i += 1
        return result
    """
    block = newblock()
    v0 = geninputarg(block, constTYPE(Signed))
    const1 = genconst(1)
    link = closeblock1(block)
    loopblock = newblock()
    result0 = geninputarg(loopblock, constTYPE(Signed))
    i0 = geninputarg(loopblock, constTYPE(Signed))
    v1 = geninputarg(loopblock, constTYPE(Signed))
    closelink(link, [const1, const1, v0], loopblock)
    const1 = genconst(1)
    result1 = genop(loopblock, 'int_mul', [result0, i0], constTYPE(Signed))
    i1 = genop(loopblock, 'int_add', [i0, const1], constTYPE(Signed))
    v2 = genop(loopblock, 'int_le', [i1, v1], constTYPE(Bool))
    false_link, true_link = closeblock2(loopblock, v2)
    closereturnlink(false_link, result1)
    closelink(true_link, [result1, i1, v1], loopblock)
    return block    

def test_loop():
    block = build_loop()
    res = runblock(block, F1, [0])
    assert res == 1
    res = runblock(block, F1, [1])
    assert res == 1
    res = runblock(block, F1, [7])
    assert res == 5040

def test_rtype_build_loop():
    blockcontainer = interpret(build_loop, [])
    res = runblock(blockcontainer, F1, [0])
    assert res == 1
    res = runblock(blockcontainer, F1, [1])
    assert res == 1
    res = runblock(blockcontainer, F1, [7])
    assert res == 5040

def test_rtype_void_constant_construction():
    def fieldname_foo():
        return constFieldName("foo")
    res = interpret(fieldname_foo, [])
    c = from_opaque_object(res)
    assert isinstance(c, flowmodel.Constant)
    assert c.concretetype == lltype.Void
    assert c.value == "foo"

    def type_Signed():
        return constTYPE(lltype.Signed)
    res = interpret(type_Signed, [])
    c = from_opaque_object(res)
    assert isinstance(c, flowmodel.Constant)
    assert c.concretetype == lltype.Void
    assert c.value == lltype.Signed

    def dummy():
        return placeholder(None)
    res = interpret(dummy, [])
    c = from_opaque_object(res)
    assert isinstance(c, flowmodel.Constant)
    assert c.concretetype == lltype.Void
    assert c.value == None

def test_rtype_revealcosnt():
    def hide_and_reveal(v):
        gv = genconst(v)
        return revealconst(lltype.Signed, gv)
    res = interpret(hide_and_reveal, [42])
    assert res == 42

    S = lltype.GcStruct('s', ('x', lltype.Signed))
    S_PTR = lltype.Ptr(S)
    def hide_and_reveal_p(p):
        gv = genconst(p)
        return revealconst(S_PTR, gv)
    s = malloc(S)
    res = interpret(hide_and_reveal_p, [s])
    assert res == s
