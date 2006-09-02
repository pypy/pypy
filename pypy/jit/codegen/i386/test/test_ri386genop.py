from pypy.rpython.lltypesystem import lltype
from pypy.rpython.llinterp import LLInterpreter
from pypy.rpython.objectmodel import keepalive_until_here
from pypy.rpython.annlowlevel import MixLevelAnnotatorPolicy
from pypy.translator.c.test.test_genc import compile
from pypy.jit.codegen.i386.ri386genop import RI386GenOp

from ctypes import c_void_p, cast, CFUNCTYPE, c_int

GENOP_POLICY = MixLevelAnnotatorPolicy(None)    # XXX clean up

# ____________________________________________________________

FUNC = lltype.FuncType([lltype.Signed], lltype.Signed)

def make_adder(rgenop, n):
    # 'return x+n'
    signed_kind = rgenop.kindToken(lltype.Signed)
    block = rgenop.newblock()
    gv_x = block.geninputarg(signed_kind)
    gv_result = block.genop2("int_add", gv_x, rgenop.genconst(n))
    link = block.close1()
    link.closereturn(gv_result)

    sigtoken = rgenop.sigToken(FUNC)
    gv_add_one = rgenop.gencallableconst(sigtoken, "adder", block)
    return gv_add_one

def runner(x, y):
    rgenop = RI386GenOp()
    gv_add_x = make_adder(rgenop, x)
    add_x = gv_add_x.revealconst(lltype.Ptr(FUNC))
    res = add_x(y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_adder_interpret():
    from pypy.jit.codegen.llgraph.rgenop import rgenop
    gv_add_5 = make_adder(rgenop, 5)
    add_5 = gv_add_5.revealconst(lltype.Ptr(FUNC))
    llinterp = LLInterpreter(None)
    res = llinterp.eval_graph(add_5._obj.graph, [12])
    assert res == 17

def test_adder_direct():
    rgenop = RI386GenOp()
    gv_add_5 = make_adder(rgenop, 5)
    print gv_add_5.value
    fnptr = cast(c_void_p(gv_add_5.value), CFUNCTYPE(c_int, c_int))
    res = fnptr(37)    # <== the segfault is here
    assert res == 42

def test_adder_compile():
    fn = compile(runner, [int, int], annotatorpolicy=GENOP_POLICY)
    res = fn(9080983, -9080941)
    assert res == 42

# ____________________________________________________________

FUNC2 = lltype.FuncType([lltype.Signed, lltype.Signed], lltype.Signed)

def make_dummy(rgenop):
    # 'return x - (y - (x-1))'
    signed_kind = rgenop.kindToken(lltype.Signed)
    block = rgenop.newblock()
    gv_x = block.geninputarg(signed_kind)
    gv_y = block.geninputarg(signed_kind)
    gv_z = block.genop2("int_sub", gv_x, rgenop.genconst(1))
    link = block.close1()

    block2 = rgenop.newblock()
    gv_y2 = block2.geninputarg(signed_kind)
    gv_z2 = block2.geninputarg(signed_kind)
    gv_x2 = block2.geninputarg(signed_kind)
    link.close([gv_y, gv_z, gv_x], block2)

    gv_s2 = block2.genop2("int_sub", gv_y2, gv_z2)
    gv_t2 = block2.genop2("int_sub", gv_x2, gv_s2)
    link2 = block2.close1()

    link2.closereturn(gv_t2)
    sigtoken = rgenop.sigToken(FUNC2)
    gv_dummyfn = rgenop.gencallableconst(sigtoken, "dummy", block)
    return gv_dummyfn

def dummy_runner(x, y):
    rgenop = RI386GenOp()
    gv_dummyfn = make_dummy(rgenop)
    dummyfn = gv_dummyfn.revealconst(lltype.Ptr(FUNC2))
    res = dummyfn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_dummy_interpret():
    from pypy.jit.codegen.llgraph.rgenop import rgenop
    gv_dummyfn = make_dummy(rgenop)
    dummyfn = gv_dummyfn.revealconst(lltype.Ptr(FUNC2))
    llinterp = LLInterpreter(None)
    res = llinterp.eval_graph(dummyfn._obj.graph, [30, 17])
    assert res == 42

def test_dummy_direct():
    rgenop = RI386GenOp()
    gv_dummyfn = make_dummy(rgenop)
    print gv_dummyfn.value
    fnptr = cast(c_void_p(gv_dummyfn.value), CFUNCTYPE(c_int, c_int, c_int))
    res = fnptr(30, 17)    # <== the segfault is here
    assert res == 42

def test_dummy_compile():
    fn = compile(dummy_runner, [int, int], annotatorpolicy=GENOP_POLICY)
    res = fn(40, 37)
    assert res == 42

# ____________________________________________________________

def make_branching(rgenop):
    # 'if x > 5: return x-1
    #  else:     return y'
    signed_kind = rgenop.kindToken(lltype.Signed)
    block = rgenop.newblock()
    gv_x = block.geninputarg(signed_kind)
    gv_y = block.geninputarg(signed_kind)
    gv_cond = block.genop2("int_gt", gv_x, rgenop.genconst(5))
    link_false, link_true = block.close2(gv_cond)

    block2 = rgenop.newblock()
    gv_one = block2.geninputarg(signed_kind)
    gv_x2 = block2.geninputarg(signed_kind)
    gv_y2 = block2.geninputarg(signed_kind)
    link_true.close([rgenop.genconst(1), gv_x, gv_y], block2)

    gv_s2 = block2.genop2("int_sub", gv_x2, gv_one)
    link2 = block2.close1()
    link2.closereturn(gv_s2)

    link_false.closereturn(gv_y)

    sigtoken = rgenop.sigToken(FUNC2)
    gv_branchingfn = rgenop.gencallableconst(sigtoken,
                                             "branching", block)
    return gv_branchingfn

def branching_runner(x, y):
    rgenop = RI386GenOp()
    gv_branchingfn = make_branching(rgenop)
    branchingfn = gv_branchingfn.revealconst(lltype.Ptr(FUNC2))
    res = branchingfn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_branching_interpret():
    from pypy.jit.codegen.llgraph.rgenop import rgenop
    gv_branchingfn = make_branching(rgenop)
    branchingfn = gv_branchingfn.revealconst(lltype.Ptr(FUNC2))
    llinterp = LLInterpreter(None)
    res = llinterp.eval_graph(branchingfn._obj.graph, [30, 17])
    assert res == 29
    res = llinterp.eval_graph(branchingfn._obj.graph, [3, 17])
    assert res == 17

def test_branching_direct():
    rgenop = RI386GenOp()
    gv_branchingfn = make_branching(rgenop)
    print gv_branchingfn.value
    fnptr = cast(c_void_p(gv_branchingfn.value), CFUNCTYPE(c_int, c_int, c_int))
    res = fnptr(30, 17)    # <== the segfault is here
    assert res == 29
    res = fnptr(3, 17)    # <== or here
    assert res == 17

def test_branching_compile():
    fn = compile(branching_runner, [int, int], annotatorpolicy=GENOP_POLICY)
    res = fn(30, 17)
    assert res == 29
    res = fn(3, 17)
    assert res == 17
