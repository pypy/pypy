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
    sigtoken = rgenop.sigToken(FUNC)
    builder, entrypoint, [gv_x] = rgenop.newgraph(sigtoken)
    gv_result = builder.genop2("int_add", gv_x, rgenop.genconst(n))
    builder.finish_and_return(sigtoken, gv_result)
    gv_add_one = rgenop.gencallableconst(sigtoken, "adder", entrypoint)
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
    sigtoken = rgenop.sigToken(FUNC2)
    builder, entrypoint, [gv_x, gv_y] = rgenop.newgraph(sigtoken)
    gv_z = builder.genop2("int_sub", gv_x, rgenop.genconst(1))

    args_gv = [gv_y, gv_z, gv_x]
    builder.enter_next_block([signed_kind, signed_kind, signed_kind], args_gv)
    [gv_y2, gv_z2, gv_x2] = args_gv

    gv_s2 = builder.genop2("int_sub", gv_y2, gv_z2)
    gv_t2 = builder.genop2("int_sub", gv_x2, gv_s2)
    builder.finish_and_return(sigtoken, gv_t2)

    gv_dummyfn = rgenop.gencallableconst(sigtoken, "dummy", entrypoint)
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
    sigtoken = rgenop.sigToken(FUNC2)
    builder, entrypoint, [gv_x, gv_y] = rgenop.newgraph(sigtoken)
    gv_cond = builder.genop2("int_gt", gv_x, rgenop.genconst(5))
    false_builder = builder.jump_if_false(gv_cond)

    # true path
    args_gv = [rgenop.genconst(1), gv_x, gv_y]
    builder.enter_next_block([signed_kind, signed_kind, signed_kind], args_gv)
    [gv_one, gv_x2, gv_y2] = args_gv

    gv_s2 = builder.genop2("int_sub", gv_x2, gv_one)
    builder.finish_and_return(sigtoken, gv_s2)

    # false path
    false_builder.finish_and_return(sigtoken, gv_y)

    # done
    gv_branchingfn = rgenop.gencallableconst(sigtoken,
                                             "branching", entrypoint)
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

# ____________________________________________________________

def make_goto(rgenop):
    # while x > 0:
    #     y += x
    #     x -= 1
    # return y
    signed_kind = rgenop.kindToken(lltype.Signed)
    sigtoken = rgenop.sigToken(FUNC2)
    builder, entrypoint, [gv_x, gv_y] = rgenop.newgraph(sigtoken)

    # loop start block
    args_gv = [gv_x, gv_y]
    loopblock = builder.enter_next_block([signed_kind, signed_kind], args_gv)
    [gv_x, gv_y] = args_gv

    gv_cond = builder.genop2("int_gt", gv_x, rgenop.genconst(0))
    bodybuilder = builder.jump_if_true(gv_cond)
    builder.finish_and_return(sigtoken, gv_y)

    # loop body
    args_gv = [gv_y, gv_x]
    bodybuilder.enter_next_block([signed_kind, signed_kind], args_gv)
    [gv_y, gv_x] = args_gv

    gv_y2 = bodybuilder.genop2("int_add", gv_x, gv_y)
    gv_x2 = bodybuilder.genop2("int_sub", gv_x, rgenop.genconst(1))
    bodybuilder.finish_and_goto([gv_x2, gv_y2], loopblock)

    # done
    gv_gotofn = rgenop.gencallableconst(sigtoken, "goto", entrypoint)
    return gv_gotofn

def goto_runner(x, y):
    rgenop = RI386GenOp()
    gv_gotofn = make_goto(rgenop)
    gotofn = gv_gotofn.revealconst(lltype.Ptr(FUNC2))
    res = gotofn(x, y)
    keepalive_until_here(rgenop)    # to keep the code blocks alive
    return res

def test_goto_interpret():
    from pypy.jit.codegen.llgraph.rgenop import rgenop
    gv_gotofn = make_goto(rgenop)
    gotofn = gv_gotofn.revealconst(lltype.Ptr(FUNC2))
    llinterp = LLInterpreter(None)
    res = llinterp.eval_graph(gotofn._obj.graph, [30, 17])
    assert res == 31 * 15 + 17
    res = llinterp.eval_graph(gotofn._obj.graph, [3, 17])
    assert res == 23

def test_goto_direct():
    rgenop = RI386GenOp()
    gv_gotofn = make_goto(rgenop)
    print gv_gotofn.value
    fnptr = cast(c_void_p(gv_gotofn.value), CFUNCTYPE(c_int, c_int, c_int))
    res = fnptr(30, 17)    # <== the segfault is here
    assert res == 31 * 15 + 17
    res = fnptr(3, 17)    # <== or here
    assert res == 23

def test_goto_compile():
    fn = compile(goto_runner, [int, int], annotatorpolicy=GENOP_POLICY)
    res = fn(30, 17)
    assert res == 31 * 15 + 17
    res = fn(3, 17)
    assert res == 23
